import random
import sqlite3
from dataclasses import fields
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import pyray as ray

from libs.animation import Animation, MoveAnimation
from libs.audio import audio
from libs.global_objects import Nameplate
from libs.texture import tex
from libs.tja import TJAParser, test_encodings
from libs.transition import Transition
from libs.utils import (
    Modifiers,
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
    session_data,
)


class State:
    BROWSING = 0
    SONG_SELECTED = 1
    DIFF_SORTING = 2

class SongSelectScreen:
    BOX_CENTER = 444
    def __init__(self, screen_width: int = 1280):
        self.screen_init = False
        self.root_dir = global_data.config["paths"]["tja_path"]
        self.screen_width = screen_width

    def load_navigator(self):
        self.navigator = FileNavigator(self.root_dir)

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(sounds_dir / "hit_sounds" / "0" / "don.wav")
        self.sound_kat = audio.load_sound(sounds_dir / "hit_sounds" / "0" / "ka.wav")
        self.sound_skip = audio.load_sound(sounds_dir / 'song_select' / 'Skip.ogg')
        self.sound_ura_switch = audio.load_sound(sounds_dir / 'song_select' / 'SE_SELECT [4].ogg')
        self.sound_add_favorite = audio.load_sound(sounds_dir / 'song_select' / 'add_favorite.ogg')
        audio.set_sound_volume(self.sound_ura_switch, 0.25)
        audio.set_sound_volume(self.sound_add_favorite, 3.0)
        self.sound_bgm = audio.load_sound(sounds_dir / "song_select" / "JINGLE_GENRE [1].ogg")

    def on_screen_start(self):
        if not self.screen_init:
            tex.load_screen_textures('song_select')
            self.load_sounds()
            self.background_move = tex.get_animation(0)
            self.move_away = tex.get_animation(1)
            self.diff_fade_out = tex.get_animation(2)
            self.text_fade_out = tex.get_animation(3)
            self.text_fade_in = tex.get_animation(4)
            self.background_fade_change = tex.get_animation(5)
            self.diff_selector_move_1 = tex.get_animation(26)
            self.diff_selector_move_2 = tex.get_animation(27)
            self.diff_select_move_right = False
            self.state = State.BROWSING
            self.selected_difficulty = -3
            self.prev_diff = -3
            self.selected_song = None
            self.game_transition = None
            self.demo_song = None
            self.diff_sort_selector = None
            self.neiro_selector = None
            self.modifier_selector = None
            self.texture_index = SongBox.DEFAULT_INDEX
            self.last_texture_index = SongBox.DEFAULT_INDEX
            self.last_moved = get_current_ms()
            self.ura_toggle = 0
            self.is_ura = False
            self.screen_init = True
            self.ura_switch_animation = UraSwitchAnimation()
            plate_info = global_data.config['nameplate']
            self.nameplate = self.nameplate = Nameplate(plate_info['name'], plate_info['title'], global_data.player_num, plate_info['dan'], plate_info['gold'])

            if self.navigator.items == []:
                return self.on_screen_end("ENTRY")

            if str(global_data.selected_song) in self.navigator.all_song_files:
                self.navigator.mark_crowns_dirty_for_song(self.navigator.all_song_files[str(global_data.selected_song)])

            self.navigator.reset_items()
            curr_item = self.navigator.get_current_item()
            curr_item.box.get_scores()
            self.navigator.add_recent()

    def on_screen_end(self, next_screen):
        self.screen_init = False
        if self.navigator.items != []:
            global_data.selected_song = self.navigator.get_current_item().path
            session_data.selected_difficulty = self.selected_difficulty
            self.reset_demo_music()
            self.navigator.reset_items()
            audio.unload_all_sounds()
            tex.unload_textures()
            self.nameplate.unload()
        return next_screen

    def reset_demo_music(self):
        if self.demo_song is not None:
            audio.stop_music_stream(self.demo_song)
            audio.unload_music_stream(self.demo_song)
            audio.play_sound(self.sound_bgm)
        self.demo_song = None
        self.navigator.get_current_item().box.wait = get_current_ms()

    def handle_input_browsing(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_LEFT_CONTROL) or (is_l_kat_pressed() and get_current_ms() <= self.last_moved + 50):
            self.reset_demo_music()
            for _ in range(10):
                self.navigator.navigate_left()
            audio.play_sound(self.sound_skip)
            self.last_moved = get_current_ms()
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_RIGHT_CONTROL) or (is_r_kat_pressed() and get_current_ms() <= self.last_moved + 50):
            self.reset_demo_music()
            for _ in range(10):
                self.navigator.navigate_right()
            audio.play_sound(self.sound_skip)
            self.last_moved = get_current_ms()
        elif is_l_kat_pressed():
            self.reset_demo_music()
            self.navigator.navigate_left()
            audio.play_sound(self.sound_kat)
            self.last_moved = get_current_ms()

        elif is_r_kat_pressed():
            self.reset_demo_music()
            self.navigator.navigate_right()
            audio.play_sound(self.sound_kat)
            self.last_moved = get_current_ms()

        # Select/Enter
        if is_l_don_pressed() or is_r_don_pressed():
            selected_item = self.navigator.items[self.navigator.selected_index]
            if selected_item is not None and selected_item.box.is_back:
                self.navigator.go_back()
                #audio.play_sound(self.sound_cancel)
            elif isinstance(selected_item, Directory) and selected_item.collection == Directory.COLLECTIONS[3]:
                self.state = State.DIFF_SORTING
                self.diff_sort_selector = DiffSortSelect()
                self.text_fade_in.start()
                self.text_fade_out.start()
            else:
                selected_song = self.navigator.select_current_item()
                if selected_song:
                    self.state = State.SONG_SELECTED
                    if 4 not in selected_song.tja.metadata.course_data:
                        self.is_ura = False
                    elif (4 in selected_song.tja.metadata.course_data and
                          3 not in selected_song.tja.metadata.course_data):
                        self.is_ura = True
                    audio.play_sound(self.sound_don)
                    self.move_away.start()
                    self.diff_fade_out.start()
                    self.text_fade_out.start()
                    self.text_fade_in.start()

        if ray.is_key_pressed(ray.KeyboardKey.KEY_SPACE):
            success = self.navigator.add_favorite()
            if success:
                audio.play_sound(self.sound_add_favorite)

    def handle_input_selected(self):
        # Handle song selection confirmation or cancel
        if self.neiro_selector is not None:
            if is_l_kat_pressed():
                self.neiro_selector.move_left()
            elif is_r_kat_pressed():
                self.neiro_selector.move_right()
            if is_l_don_pressed() or is_r_don_pressed():
                audio.play_sound(self.sound_don)
                self.neiro_selector.confirm()
            return
        if self.modifier_selector is not None:
            if is_l_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.modifier_selector.left()
            elif is_r_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.modifier_selector.right()
            if is_l_don_pressed() or is_r_don_pressed():
                audio.play_sound(self.sound_don)
                self.modifier_selector.confirm()
            return
        if is_l_don_pressed() or is_r_don_pressed():
            if self.selected_difficulty == -3:
                self._cancel_selection()
            elif self.selected_difficulty == -2:
                audio.play_sound(self.sound_don)
                self.modifier_selector = ModifierSelector()
            elif self.selected_difficulty == -1:
                audio.play_sound(self.sound_don)
                self.neiro_selector = NeiroSelector()
            else:
                self._confirm_selection()

        def get_current_song():
            selected_song = self.navigator.get_current_item()
            if isinstance(selected_song, Directory):
                raise Exception("Directory was chosen instead of song")
            return selected_song

        if is_l_kat_pressed() or is_r_kat_pressed():
            audio.play_sound(self.sound_kat)
            selected_song = get_current_song()
            diffs = sorted(selected_song.tja.metadata.course_data)

            if is_l_kat_pressed():
                self._navigate_difficulty_left(diffs)
            else:  # is_r_kat_pressed()
                self._navigate_difficulty_right(diffs)

        if (ray.is_key_pressed(ray.KeyboardKey.KEY_TAB) and
            self.selected_difficulty in [3, 4]):
            self._toggle_ura_mode()

    def handle_input_diff_sort(self):
        if self.diff_sort_selector is None:
            raise Exception("Diff sort selector was not able to be created")
        if is_l_kat_pressed():
            self.diff_sort_selector.input_left()
            audio.play_sound(self.sound_kat)
        if is_r_kat_pressed():
            self.diff_sort_selector.input_right()
            audio.play_sound(self.sound_kat)
        if is_l_don_pressed() or is_r_don_pressed():
            tuple = self.diff_sort_selector.input_select()
            audio.play_sound(self.sound_don)
            if tuple is None:
                return
            diff, level = tuple
            self.diff_sort_selector = None
            self.state = State.BROWSING
            self.text_fade_out.reset()
            self.text_fade_in.reset()
            if diff != -1:
                if level != -1:
                    self.navigator.diff_sort_diff = diff
                    self.navigator.diff_sort_level = level
                self.navigator.select_current_item()

    def _cancel_selection(self):
        """Reset to browsing state"""
        self.selected_song = None
        self.move_away.reset()
        self.diff_fade_out.reset()
        self.text_fade_out.reset()
        self.text_fade_in.reset()
        self.state = State.BROWSING
        self.navigator.reset_items()


    def _confirm_selection(self):
        """Confirm song selection and create game transition"""
        audio.play_sound(self.sound_don)
        selected_song = self.navigator.get_current_item()
        if not isinstance(selected_song, SongFile):
            raise Exception("picked directory")

        title = selected_song.tja.metadata.title.get(
            global_data.config['general']['language'], '')
        subtitle = selected_song.tja.metadata.subtitle.get(
            global_data.config['general']['language'], '')
        self.game_transition = Transition(title, subtitle)
        self.game_transition.start()

    def _navigate_difficulty_left(self, diffs):
        """Navigate difficulty selection leftward"""
        self.diff_select_move_right = False
        if self.is_ura and self.selected_difficulty == 4:
            self.diff_selector_move_1.start()
            self.prev_diff = self.selected_difficulty
            if len(diffs) == 1:
                self.selected_difficulty = -1
            else:
                self.selected_difficulty = diffs[-2]
        elif self.selected_difficulty == -1 or self.selected_difficulty == -2:
            self.diff_selector_move_2.start()
            self.prev_diff = self.selected_difficulty
            self.selected_difficulty -= 1
        elif self.selected_difficulty == -3:
            pass
        elif self.selected_difficulty not in diffs:
            self.prev_diff = self.selected_difficulty
            self.diff_selector_move_1.start()
            self.selected_difficulty = min(diffs)
        elif self.selected_difficulty == min(diffs):
            self.diff_selector_move_2.start()
            self.prev_diff = self.selected_difficulty
            self.selected_difficulty = -1
        else:
            self.diff_selector_move_1.start()
            self.prev_diff = self.selected_difficulty
            self.selected_difficulty = diffs[diffs.index(self.selected_difficulty) - 1]

    def _navigate_difficulty_right(self, diffs):
        """Navigate difficulty selection rightward"""
        self.diff_select_move_right = True
        if self.is_ura and self.selected_difficulty == 2:
            self.prev_diff = self.selected_difficulty
            self.selected_difficulty = 4
            self.diff_selector_move_1.start()

        if (self.selected_difficulty in [3, 4] and 4 in diffs and 3 in diffs):
            self.ura_toggle = (self.ura_toggle + 1) % 10
            if self.ura_toggle == 0:
                self._toggle_ura_mode()
        elif self.selected_difficulty == -1:
            self.prev_diff = self.selected_difficulty
            self.selected_difficulty = min(diffs)
            self.diff_selector_move_2.start()
            self.diff_selector_move_1.start()
        elif self.selected_difficulty == -2 or self.selected_difficulty == -3:
            self.prev_diff = self.selected_difficulty
            self.selected_difficulty += 1
            self.diff_selector_move_2.start()
        elif self.selected_difficulty < max(diffs):
            self.prev_diff = self.selected_difficulty
            self.selected_difficulty = diffs[diffs.index(self.selected_difficulty) + 1]
            self.diff_selector_move_1.start()

    def _toggle_ura_mode(self):
        """Toggle between ura and normal mode"""
        self.ura_toggle = 0
        self.is_ura = not self.is_ura
        self.ura_switch_animation.start(not self.is_ura)
        audio.play_sound(self.sound_ura_switch)
        self.selected_difficulty = 7 - self.selected_difficulty

    def handle_input(self):
        if self.state == State.BROWSING:
            self.handle_input_browsing()
        elif self.state == State.SONG_SELECTED:
            self.handle_input_selected()
        elif self.state == State.DIFF_SORTING:
            self.handle_input_diff_sort()

    def update(self):
        ret_val = self.on_screen_start()
        if ret_val is not None:
            return ret_val
        self.background_move.update(get_current_ms())
        self.move_away.update(get_current_ms())
        self.diff_fade_out.update(get_current_ms())
        self.background_fade_change.update(get_current_ms())
        self.text_fade_out.update(get_current_ms())
        self.text_fade_in.update(get_current_ms())
        self.ura_switch_animation.update(get_current_ms())
        self.diff_selector_move_1.update(get_current_ms())
        self.diff_selector_move_2.update(get_current_ms())
        self.nameplate.update(get_current_ms())

        if self.text_fade_out.is_finished:
            self.selected_song = True

        if self.last_texture_index != self.texture_index:
            if not self.background_fade_change.is_started:
                self.background_fade_change.start()
            if self.background_fade_change.is_finished:
                self.last_texture_index = self.texture_index
                self.background_fade_change.reset()

        if self.game_transition is not None:
            self.game_transition.update(get_current_ms())
            if self.game_transition.is_finished:
                return self.on_screen_end("GAME")
        else:
            self.handle_input()

        if self.demo_song is not None:
            audio.update_music_stream(self.demo_song)

        if self.navigator.genre_bg is not None:
            self.navigator.genre_bg.update(get_current_ms())

        if self.diff_sort_selector is not None:
            self.diff_sort_selector.update(get_current_ms())

        if self.neiro_selector is not None:
            self.neiro_selector.update(get_current_ms())
            if self.neiro_selector.is_finished:
                self.neiro_selector = None

        if self.modifier_selector is not None:
            self.modifier_selector.update(get_current_ms())
            if self.modifier_selector.is_finished:
                self.modifier_selector = None

        for song in self.navigator.items:
            song.box.update(self.state == State.SONG_SELECTED)
            song.box.is_open = song.box.position == SongSelectScreen.BOX_CENTER + 150
            if not isinstance(song, Directory) and song.box.is_open:
                if self.demo_song is None and get_current_ms() >= song.box.wait + (83.33*3):
                    song.box.get_scores()
                    if song.tja.metadata.wave.exists() and song.tja.metadata.wave.is_file():
                        self.demo_song = audio.load_music_stream(song.tja.metadata.wave, preview=song.tja.metadata.demostart)
                        audio.play_music_stream(self.demo_song)
                        audio.stop_sound(self.sound_bgm)
            if song.box.is_open:
                current_box = song.box
                if not current_box.is_back and get_current_ms() >= song.box.wait + (83.33*3):
                    self.texture_index = current_box.texture_index

        if ray.is_key_pressed(ray.KeyboardKey.KEY_ESCAPE):
            return self.on_screen_end('ENTRY')

    def draw_selector(self):
        fade = 0.5 if (self.neiro_selector is not None or self.modifier_selector is not None) else self.text_fade_in.attribute
        direction = 1 if self.diff_select_move_right else -1
        if self.selected_difficulty <= -1 or self.prev_diff == -1:
            if self.prev_diff == -1 and self.selected_difficulty >= 0:
                if not self.diff_selector_move_2.is_finished:
                    tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_balloon', x=((self.prev_diff+3) * 70) - 220 + (self.diff_selector_move_2.attribute * direction), fade=fade)
                    tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_outline_back', x=((self.prev_diff+3) * 70) + (self.diff_selector_move_2.attribute * direction))
                else:
                    difficulty = min(3, self.selected_difficulty)
                    tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_balloon', x=(difficulty * 115), fade=fade)
                    tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_outline', x=(difficulty * 115))
            elif not self.diff_selector_move_2.is_finished:
                tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_outline_back', x=((self.prev_diff+3) * 70) + (self.diff_selector_move_2.attribute * direction))
                if self.selected_difficulty != -3:
                    tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_balloon', x=((self.prev_diff+3) * 70) - 220 + (self.diff_selector_move_2.attribute * direction), fade=fade)
            else:
                tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_outline_back', x=((self.selected_difficulty+3) * 70))
                if self.selected_difficulty != -3:
                    tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_balloon', x=((self.selected_difficulty+3) * 70) - 220, fade=fade)
        else:
            if self.prev_diff == -1:
                return
            if not self.diff_selector_move_1.is_finished:
                difficulty = min(3, self.prev_diff)
                tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_balloon', x=(difficulty * 115) + (self.diff_selector_move_1.attribute * direction), fade=fade)
                tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_outline', x=(difficulty * 115) + (self.diff_selector_move_1.attribute * direction))
            else:
                difficulty = min(3, self.selected_difficulty)
                tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_balloon', x=(difficulty * 115), fade=fade)
                tex.draw_texture('diff_select', f'{str(global_data.player_num)}p_outline', x=(difficulty * 115))

    def draw(self):
        width = tex.textures['box']['background'].width
        for i in range(0, width * 4, width):
            tex.draw_texture('box', 'background', frame=self.last_texture_index, x=i-self.background_move.attribute)
            tex.draw_texture('box', 'background', frame=self.texture_index, x=i-self.background_move.attribute, fade=1 - self.background_fade_change.attribute)

        if self.navigator.genre_bg is not None and self.state == State.BROWSING:
            self.navigator.genre_bg.draw(95)

        for item in self.navigator.items:
            box = item.box
            if -156 <= box.position <= self.screen_width + 144:
                if box.position <= 500:
                    box.draw(box.position - int(self.move_away.attribute), 95, self.is_ura, fade_override=self.diff_fade_out.attribute)
                else:
                    box.draw(box.position + int(self.move_away.attribute), 95, self.is_ura, fade_override=self.diff_fade_out.attribute)

        tex.draw_texture('global', 'footer')

        if self.nameplate.player_num == 1:
            self.nameplate.draw(30, 640)
        else:
            self.nameplate.draw(950, 640)

        self.ura_switch_animation.draw()

        if self.state == State.BROWSING and self.navigator.items != []:
            self.navigator.get_current_item().box.draw_score_history()
        if self.diff_sort_selector is not None:
            self.diff_sort_selector.draw()

        if (self.selected_song and self.state == State.SONG_SELECTED):
            self.draw_selector()
            tex.draw_texture('global', 'difficulty_select', fade=self.text_fade_in.attribute)
        elif self.state == State.DIFF_SORTING:
            tex.draw_texture('global', 'difficulty_select', fade=self.text_fade_in.attribute)
        else:
            tex.draw_texture('global', 'song_select', fade=self.text_fade_out.attribute)

        if self.neiro_selector is not None:
            self.neiro_selector.draw()

        if self.modifier_selector is not None:
            self.modifier_selector.draw()

        if self.game_transition is not None:
            self.game_transition.draw()

    def draw_3d(self):
        pass

class SongBox:
    OUTLINE_MAP = {
        1: ray.Color(0, 77, 104, 255),
        2: ray.Color(156, 64, 2, 255),
        3: ray.Color(84, 101, 126, 255),
        4: ray.Color(153, 4, 46, 255),
        5: ray.Color(60, 104, 0, 255),
        6: ray.Color(134, 88, 0, 255),
        7: ray.Color(79, 40, 134, 255),
        8: ray.Color(148, 24, 0, 255),
        9: ray.Color(101, 0, 82, 255),
        10: ray.Color(140, 39, 92, 255),
        11: ray.Color(151, 57, 30, 255),
        12: ray.Color(35, 123, 103, 255),
        13: ray.Color(25, 68, 137, 255),
        14: ray.Color(157, 13, 31, 255)
    }
    BACK_INDEX = 17
    DEFAULT_INDEX = 9
    def __init__(self, name: str, texture_index: int, is_dir: bool, tja: Optional[TJAParser] = None,
        tja_count: Optional[int] = None, box_texture: Optional[str] = None, name_texture_index: Optional[int] = None):
        self.text_name = name
        self.texture_index = texture_index
        if name_texture_index is None:
            self.name_texture_index = texture_index
        else:
            self.name_texture_index = name_texture_index
        self.box_texture_path = box_texture
        self.box_texture = None
        self.scores = dict()
        self.crown = dict()
        self.position = -11111
        self.start_position = -1
        self.target_position = -1
        self.is_open = False
        self.is_back = self.texture_index == SongBox.BACK_INDEX
        self.name = None
        self.black_name = None
        self.hori_name = None
        self.yellow_box = None
        self.open_anim = Animation.create_move(133, start_position=0, total_distance=150, delay=83.33)
        self.open_fade = Animation.create_fade(200, initial_opacity=0, final_opacity=1.0)
        self.move = None
        self.wait = 0
        self.is_dir = is_dir
        self.tja_count = tja_count
        self.tja_count_text = None
        self.score_history = None
        self.history_wait = 0
        self.tja = tja
        self.hash = dict()

    def reset(self):
        if self.yellow_box is not None:
            self.yellow_box.reset()
            self.yellow_box.create_anim()
        if self.name is not None:
            self.name.unload()
            self.name = None
        if self.box_texture is not None:
            ray.unload_texture(self.box_texture)
            self.box_texture = None
        if self.black_name is not None:
            self.black_name.unload()
            self.black_name = None
        if self.hori_name is not None:
            self.hori_name.unload()
            self.hori_name = None
        self.is_open = False

    def get_scores(self):
        if self.tja is None:
            return
        with sqlite3.connect('scores.db') as con:
            cursor = con.cursor()
            # Batch database query for all diffs at once
            if self.tja.metadata.course_data:
                hash_values = [self.hash[diff] for diff in self.tja.metadata.course_data]
                placeholders = ','.join('?' * len(hash_values))

                batch_query = f"""
                    SELECT hash, score, good, ok, bad, clear
                    FROM Scores
                    WHERE hash IN ({placeholders})
                """
                cursor.execute(batch_query, hash_values)

                hash_to_score = {row[0]: row[1:] for row in cursor.fetchall()}

                for diff in self.tja.metadata.course_data:
                    diff_hash = self.hash[diff]
                    self.scores[diff] = hash_to_score.get(diff_hash)

    def move_box(self):
        if self.position != self.target_position and self.move is None:
            if self.position < self.target_position:
                direction = 1
            else:
                direction = -1
            if abs(self.target_position - self.position) > 250:
                direction *= -1
            self.move = Animation.create_move(83.3, start_position=0, total_distance=100 * direction, ease_out='cubic')
            self.move.start()
            if self.is_open or self.target_position == SongSelectScreen.BOX_CENTER + 150:
                self.move.total_distance = 250 * direction
            self.start_position = self.position
        if self.move is not None:
            self.move.update(get_current_ms())
            self.position = self.start_position + int(self.move.attribute)
            if self.move.is_finished:
                self.position = self.target_position
                self.move = None

    def update(self, is_diff_select):
        self.is_diff_select = is_diff_select
        is_open_prev = self.is_open
        self.move_box()
        self.is_open = self.position == SongSelectScreen.BOX_CENTER + 150

        if not (-56 <= self.position <= 1280):
            return
        if self.yellow_box is not None:
            self.yellow_box.update(is_diff_select)

        if self.history_wait == 0:
            self.history_wait = get_current_ms()

        if self.score_history is None and {k: v for k, v in self.scores.items() if v is not None}:
            self.score_history = ScoreHistory(self.scores, get_current_ms())

        if not is_open_prev and self.is_open:
            if self.black_name is None:
                self.black_name = OutlinedText(self.text_name, 40, ray.WHITE, ray.BLACK, outline_thickness=5, vertical=True)
            if self.tja is not None or self.is_back:
                self.yellow_box = YellowBox(self.black_name, self.is_back, tja=self.tja)
                self.yellow_box.create_anim()
            else:
                self.hori_name = OutlinedText(self.text_name, 40, ray.WHITE, ray.BLACK, outline_thickness=5)
                self.open_anim.start()
                self.open_fade.start()
            self.wait = get_current_ms()
            if get_current_ms() >= self.history_wait + 3000:
                self.history_wait = get_current_ms()
        if self.tja_count is not None and self.tja_count > 0 and self.tja_count_text is None:
            self.tja_count_text = OutlinedText(str(self.tja_count), 35, ray.WHITE, ray.BLACK, outline_thickness=5)#, horizontal_spacing=1.2)
        if self.box_texture is None and self.box_texture_path is not None:
            self.box_texture = ray.load_texture(self.box_texture_path)

        self.open_anim.update(get_current_ms())
        self.open_fade.update(get_current_ms())

        if self.name is None:
            self.name = OutlinedText(self.text_name, 40, ray.WHITE, SongBox.OUTLINE_MAP.get(self.name_texture_index, ray.Color(101, 0, 82, 255)), outline_thickness=5, vertical=True)

        if self.score_history is not None:
            self.score_history.update(get_current_ms())


    def _draw_closed(self, x: int, y: int):
        tex.draw_texture('box', 'folder_texture_left', frame=self.texture_index, x=x)
        offset = 1 if self.texture_index == 3 or self.texture_index >= 9 and self.texture_index not in {10,11,12} else 0
        tex.draw_texture('box', 'folder_texture', frame=self.texture_index, x=x, x2=32, y=offset)
        tex.draw_texture('box', 'folder_texture_right', frame=self.texture_index, x=x)
        if self.texture_index == SongBox.DEFAULT_INDEX:
            tex.draw_texture('box', 'genre_overlay', x=x, y=y)
        elif self.texture_index == 14:
            tex.draw_texture('box', 'diff_overlay', x=x, y=y)
        if not self.is_back and self.is_dir:
            tex.draw_texture('box', 'folder_clip', frame=self.texture_index, x=x - (1 - offset), y=y)

        if self.is_back:
            tex.draw_texture('box', 'back_text', x=x, y=y)
        elif self.name is not None:
            dest = ray.Rectangle(x + 47 - int(self.name.texture.width / 2), y+35, self.name.texture.width, min(self.name.texture.height, 417))
            self.name.draw(self.name.default_src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        if self.tja is not None and self.tja.ex_data.new:
            tex.draw_texture('yellow_box', 'ex_data_new_song_balloon', x=x, y=y)
        valid_scores = {k: v for k, v in self.scores.items() if v is not None}
        if valid_scores:
            highest_key = max(valid_scores.keys())
            score = self.scores[highest_key]
            if score and score[3] == 0:
                tex.draw_texture('yellow_box', 'crown_fc', x=x, y=y, frame=highest_key)
            elif score and score[4] == 1:
                tex.draw_texture('yellow_box', 'crown_clear', x=x, y=y, frame=highest_key)
        if self.crown: #Folder lamp
            highest_crown = max(self.crown)
            if self.crown[highest_crown] == 'FC':
                tex.draw_texture('yellow_box', 'crown_fc', x=x, y=y, frame=highest_crown)
            else:
                tex.draw_texture('yellow_box', 'crown_clear', x=x, y=y, frame=highest_crown)

    def _draw_open(self, x: int, y: int, fade_override: Optional[float]):
        color = ray.WHITE
        if fade_override is not None:
            color = ray.fade(ray.WHITE, fade_override)
        if self.hori_name is not None and self.open_anim.attribute >= 100:
            tex.draw_texture('box', 'folder_top_edge', x=x, y=y - self.open_anim.attribute, color=color, mirror='horizontal', frame=self.texture_index)
            tex.draw_texture('box', 'folder_top', x=x, y=y - self.open_anim.attribute, color=color, frame=self.texture_index)
            tex.draw_texture('box', 'folder_top_edge', x=x+268, y=y - self.open_anim.attribute, color=color, frame=self.texture_index)
            dest_width = min(300, self.hori_name.texture.width)
            dest = ray.Rectangle((x + 48) - (dest_width//2), y + 107 - self.open_anim.attribute, dest_width, self.hori_name.texture.height)
            self.hori_name.draw(self.hori_name.default_src, dest, ray.Vector2(0, 0), 0, color)

        tex.draw_texture('box', 'folder_texture_left', frame=self.texture_index, x=x - self.open_anim.attribute)
        offset = 1 if self.texture_index == 3 or self.texture_index >= 9 and self.texture_index not in {10,11,12} else 0
        tex.draw_texture('box', 'folder_texture', frame=self.texture_index, x=x - self.open_anim.attribute, y=offset, x2=(self.open_anim.attribute*2)+32)
        tex.draw_texture('box', 'folder_texture_right', frame=self.texture_index, x=x + self.open_anim.attribute)

        if self.texture_index == SongBox.DEFAULT_INDEX:
            tex.draw_texture('box', 'genre_overlay_large', x=x, y=y, color=color)
        elif self.texture_index == 14:
            tex.draw_texture('box', 'diff_overlay_large', x=x, y=y, color=color)

        color = ray.WHITE
        if fade_override is not None:
            color = ray.fade(ray.WHITE, fade_override)
        if self.tja_count_text is not None and self.texture_index != 14:
            tex.draw_texture('yellow_box', 'song_count_back', color=color, fade=0.5)
            tex.draw_texture('yellow_box', 'song_count_num', color=color)
            tex.draw_texture('yellow_box', 'song_count_songs', color=color)
            dest_width = min(124, self.tja_count_text.texture.width)
            dest = ray.Rectangle(560 - (dest_width//2), 126, dest_width, self.tja_count_text.texture.height)
            self.tja_count_text.draw(self.tja_count_text.default_src, dest, ray.Vector2(0, 0), 0, color)
        if self.texture_index != 9:
            tex.draw_texture('box', 'folder_graphic', color=color, frame=self.texture_index)
            tex.draw_texture('box', 'folder_text', color=color, frame=self.texture_index)
        elif self.box_texture is not None:
            ray.draw_texture(self.box_texture, (x+48) - (self.box_texture.width//2), (y+240) - (self.box_texture.height//2), color)

    def draw_score_history(self):
        if self.is_open and get_current_ms() >= self.wait + 83.33:
            if self.score_history is not None and get_current_ms() >= self.history_wait + 3000:
                self.score_history.draw()
    def draw(self, x: int, y: int, is_ura: bool, fade_override=None):
        if self.is_open and get_current_ms() >= self.wait + 83.33:
            if self.yellow_box is not None:
                self.yellow_box.draw(self, fade_override, is_ura)
            else:
                self._draw_open(x, y, self.open_fade.attribute)
        else:
            self._draw_closed(x, y)

class YellowBox:
    def __init__(self, name: OutlinedText, is_back: bool, tja: Optional[TJAParser] = None):
        self.is_diff_select = False
        self.name = name
        self.is_back = is_back
        self.tja = tja
        self.subtitle = None
        if self.tja is not None:
            subtitle_text = self.tja.metadata.subtitle.get(global_data.config['general']['language'], '')
            font_size = 30 if len(subtitle_text) < 30 else 20
            self.subtitle = OutlinedText(subtitle_text, font_size, ray.WHITE, ray.BLACK, outline_thickness=5, vertical=True)

        self.left_out = tex.get_animation(9)
        self.right_out = tex.get_animation(10)
        self.center_out = tex.get_animation(11)
        self.fade = tex.get_animation(12)

        self.left_out.reset()
        self.right_out.reset()
        self.center_out.reset()
        self.fade.reset()

        self.left_out_2 = tex.get_animation(13)
        self.right_out_2 = tex.get_animation(14)
        self.center_out_2 = tex.get_animation(15)
        self.top_y_out = tex.get_animation(16)
        self.center_h_out = tex.get_animation(17)
        self.fade_in = tex.get_animation(18)

        self.right_out_2.reset()
        self.top_y_out.reset()
        self.center_h_out.reset()

        self.right_x = self.right_out.attribute
        self.left_x = self.left_out.attribute
        self.center_width = self.center_out.attribute
        self.top_y = self.top_y_out.attribute
        self.center_height = self.center_h_out.attribute
        self.bottom_y = tex.textures['yellow_box']['yellow_box_bottom_right'].y[0]
        self.edge_height = tex.textures['yellow_box']['yellow_box_bottom_right'].height

    def reset(self):
        if self.subtitle is not None:
            self.subtitle.unload()
            self.subtitle = None

    def create_anim(self):
        self.right_out_2.reset()
        self.top_y_out.reset()
        self.center_h_out.reset()
        self.left_out.start()
        self.right_out.start()
        self.center_out.start()
        self.fade.start()

    def create_anim_2(self):
        self.left_out_2.start()
        self.right_out_2.start()
        self.center_out_2.start()
        self.top_y_out.start()
        self.center_h_out.start()
        self.fade_in.start()

    def update(self, is_diff_select: bool):
        self.left_out.update(get_current_ms())
        self.right_out.update(get_current_ms())
        self.center_out.update(get_current_ms())
        self.fade.update(get_current_ms())
        self.fade_in.update(get_current_ms())
        self.left_out_2.update(get_current_ms())
        self.right_out_2.update(get_current_ms())
        self.center_out_2.update(get_current_ms())
        self.top_y_out.update(get_current_ms())
        self.center_h_out.update(get_current_ms())
        if is_diff_select and not self.is_diff_select:
            self.create_anim_2()
        if self.is_diff_select:
            self.right_x = self.right_out_2.attribute
            self.left_x = self.left_out_2.attribute
            self.top_y = self.top_y_out.attribute
            self.center_width = self.center_out_2.attribute
            self.center_height = self.center_h_out.attribute
        else:
            self.right_x = self.right_out.attribute
            self.left_x = self.left_out.attribute
            self.center_width = self.center_out.attribute
            self.top_y = self.top_y_out.attribute
            self.center_height = self.center_h_out.attribute
        self.is_diff_select = is_diff_select

    def _draw_tja_data(self, song_box, color, fade):
        if self.tja is None:
            return
        for diff in self.tja.metadata.course_data:
            if diff >= 4:
                continue
            elif diff in song_box.scores and song_box.scores[diff] is not None and song_box.scores[diff][3] == 0:
                tex.draw_texture('yellow_box', 's_crown_fc', x=(diff*60), color=color)
            elif diff in song_box.scores and song_box.scores[diff] is not None and song_box.scores[diff][4] == 1:
                tex.draw_texture('yellow_box', 's_crown_clear', x=(diff*60), color=color)
            tex.draw_texture('yellow_box', 's_crown_outline', x=(diff*60), fade=min(fade, 0.25))

        if self.tja.ex_data.new_audio:
            tex.draw_texture('yellow_box', 'ex_data_new_audio', color=color)
        elif self.tja.ex_data.old_audio:
            tex.draw_texture('yellow_box', 'ex_data_old_audio', color=color)
        elif self.tja.ex_data.limited_time:
            tex.draw_texture('yellow_box', 'ex_data_limited_time', color=color)
        elif self.tja.ex_data.new:
            tex.draw_texture('yellow_box', 'ex_data_new_song', color=color)

        for i in range(4):
            tex.draw_texture('yellow_box', 'difficulty_bar', frame=i, x=(i*60), color=color)
            if i not in self.tja.metadata.course_data:
                tex.draw_texture('yellow_box', 'difficulty_bar_shadow', frame=i, x=(i*60), fade=min(fade, 0.25))

        for diff in self.tja.metadata.course_data:
            if diff >= 4:
                continue
            for j in range(self.tja.metadata.course_data[diff].level):
                tex.draw_texture('yellow_box', 'star', x=(diff*60), y=(j*-17), color=color)

    def _draw_tja_data_diff(self, is_ura: bool):
        if self.tja is None:
            return
        tex.draw_texture('diff_select', 'back', fade=self.fade_in.attribute)
        tex.draw_texture('diff_select', 'option', fade=self.fade_in.attribute)
        tex.draw_texture('diff_select', 'neiro', fade=self.fade_in.attribute)

        for i in range(4):
            if i == 3 and is_ura:
                tex.draw_texture('diff_select', 'diff_tower', frame=4, x=(i*115), fade=self.fade_in.attribute)
                tex.draw_texture('diff_select', 'ura_oni_plate', fade=self.fade_in.attribute)
            else:
                tex.draw_texture('diff_select', 'diff_tower', frame=i, x=(i*115), fade=self.fade_in.attribute)
            if i not in self.tja.metadata.course_data:
                tex.draw_texture('diff_select', 'diff_tower_shadow', frame=i, x=(i*115), fade=min(self.fade_in.attribute, 0.25))

        for course in self.tja.metadata.course_data:
            if (course == 4 and not is_ura) or (course == 3 and is_ura):
                continue
            for j in range(self.tja.metadata.course_data[course].level):
                tex.draw_texture('yellow_box', 'star_ura', x=min(course, 3)*115, y=(j*-20), fade=self.fade_in.attribute)

    def _draw_text(self, song_box):
        if not isinstance(self.right_out, MoveAnimation):
            return
        if not isinstance(self.right_out_2, MoveAnimation):
            return
        if not isinstance(self.top_y_out, MoveAnimation):
            return
        x = song_box.position + (self.right_out.attribute*0.85 - (self.right_out.start_position*0.85)) + self.right_out_2.attribute - self.right_out_2.start_position
        if self.is_back:
            tex.draw_texture('box', 'back_text_highlight', x=x)
        elif self.name is not None:
            texture = self.name.texture
            dest = ray.Rectangle(x + 30, 35 + self.top_y_out.attribute, texture.width, min(texture.height, 417))
            self.name.draw(self.name.default_src, dest, ray.Vector2(0, 0), 0, ray.WHITE)
        if self.subtitle is not None:
            texture = self.subtitle.texture
            y = self.bottom_y - min(texture.height, 410) + 10 + self.top_y_out.attribute - self.top_y_out.start_position
            dest = ray.Rectangle(x - 15, y, texture.width, min(texture.height, 410))
            self.subtitle.draw(self.subtitle.default_src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

    def _draw_yellow_box(self):
        tex.draw_texture('yellow_box', 'yellow_box_bottom_right', x=self.right_x)
        tex.draw_texture('yellow_box', 'yellow_box_bottom_left', x=self.left_x, y=self.bottom_y)
        tex.draw_texture('yellow_box', 'yellow_box_top_right', x=self.right_x, y=self.top_y)
        tex.draw_texture('yellow_box', 'yellow_box_top_left', x=self.left_x, y=self.top_y)
        tex.draw_texture('yellow_box', 'yellow_box_bottom', x=self.left_x + self.edge_height, y=self.bottom_y, x2=self.center_width)
        tex.draw_texture('yellow_box', 'yellow_box_right', x=self.right_x, y=self.top_y + self.edge_height, y2=self.center_height)
        tex.draw_texture('yellow_box', 'yellow_box_left', x=self.left_x, y=self.top_y + self.edge_height, y2=self.center_height)
        tex.draw_texture('yellow_box', 'yellow_box_top', x=self.left_x + self.edge_height, y=self.top_y, x2=self.center_width)
        tex.draw_texture('yellow_box', 'yellow_box_center', x=self.left_x + self.edge_height, y=self.top_y + self.edge_height, x2=self.center_width, y2=self.center_height)

    def draw(self, song_box: SongBox, fade_override: Optional[float], is_ura: bool):
        self._draw_yellow_box()
        if self.is_diff_select and self.tja is not None:
            self._draw_tja_data_diff(is_ura)
        else:
            fade = self.fade.attribute
            if fade_override is not None:
                fade = min(self.fade.attribute, fade_override)
            if self.is_back:
                tex.draw_texture('box', 'back_graphic', fade=fade)
            self._draw_tja_data(song_box, ray.fade(ray.WHITE, fade), fade)

        self._draw_text(song_box)

class GenreBG:
    def __init__(self, start_box: SongBox, end_box: SongBox, title: OutlinedText, diff_sort: Optional[int]):
        self.start_box = start_box
        self.end_box = end_box
        self.start_position = start_box.position
        self.end_position = end_box.position
        self.title = title
        self.fade_in = Animation.create_fade(116, initial_opacity=0.0, final_opacity=1.0, ease_in='quadratic', delay=50)
        self.fade_in.start()
        self.diff_num = diff_sort
    def update(self, current_ms):
        self.start_position = self.start_box.position
        self.end_position = self.end_box.position
        self.fade_in.update(current_ms)
    def draw(self, y):
        offset = -150 if self.start_box.is_open else 0

        tex.draw_texture('box', 'folder_background_edge', frame=self.end_box.texture_index, x=self.start_position+offset, y=y, mirror="horizontal", fade=self.fade_in.attribute)


        extra_distance = 155 if self.end_box.is_open or (self.start_box.is_open and 844 <= self.end_position <= 1144) else 0
        if self.start_position >= -56 and self.end_position < self.start_position:
            x2 = self.start_position + 1400
            x = self.start_position+offset
        elif (self.start_position <= -56) and (self.end_position < self.start_position):
            x = 0
            x2 = 1280
        else:
            x2 = abs(self.end_position) - self.start_position + extra_distance + 57
            x = self.start_position+offset
        tex.draw_texture('box', 'folder_background', x=x, y=y, x2=x2, frame=self.end_box.texture_index)


        if self.end_position < self.start_position and self.end_position >= -56:
            x2 = min(self.end_position+75, 1280) + extra_distance
            tex.draw_texture('box', 'folder_background', x=-18, y=y, x2=x2, frame=self.end_box.texture_index)


        offset = 150 if self.end_box.is_open else 0
        tex.draw_texture('box', 'folder_background_edge', x=self.end_position+80+offset, y=y, fade=self.fade_in.attribute, frame=self.end_box.texture_index)

        if ((self.start_position <= 594 and self.end_position >= 594) or
            ((self.start_position <= 594 or self.end_position >= 594) and (self.start_position > self.end_position))):
            offset = 100 if self.diff_num is not None else 0
            dest_width = min(300, self.title.texture.width)
            tex.draw_texture('box', 'folder_background_folder', x=-((offset+dest_width)//2), y=y-2, x2=dest_width+offset - 10, fade=self.fade_in.attribute, frame=self.end_box.texture_index)
            tex.draw_texture('box', 'folder_background_folder_edge', x=-((offset+dest_width)//2), y=y-2, fade=self.fade_in.attribute, frame=self.end_box.texture_index, mirror="horizontal")
            tex.draw_texture('box', 'folder_background_folder_edge', x=((offset+dest_width)//2)+20, y=y-2, fade=self.fade_in.attribute, frame=self.end_box.texture_index)
            if self.diff_num is not None:
                tex.draw_texture('diff_sort', 'star_num', frame=self.diff_num, x=-150 + (dest_width//2), y=-143)
            dest = ray.Rectangle((1280//2) - (dest_width//2)-(offset//2), y-60, dest_width, self.title.texture.height)
            self.title.draw(self.title.default_src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, self.fade_in.attribute))

class UraSwitchAnimation:
    def __init__(self) -> None:
        self.texture_change = tex.get_animation(7)
        self.fade_out = tex.get_animation(8)
        self.fade_out.attribute = 0
    def start(self, is_backwards: bool):
        if is_backwards:
            self.texture_change = tex.get_animation(6)
        self.texture_change.start()
        self.fade_out.start()

    def update(self, current_ms: float):
        self.texture_change.update(current_ms)
        self.fade_out.update(current_ms)
    def draw(self):
        tex.draw_texture('diff_select', 'ura_switch', frame=self.texture_change.attribute, fade=self.fade_out.attribute)

class DiffSortSelect:
    def __init__(self):
        self.selected_box = -1
        self.selected_level = 1
        self.in_level_select = False
        self.confirmation = False
        self.confirm_index = 1
        self.num_boxes = 6
        self.limits = [5, 7, 8, 10]

        self.bg_resize = tex.get_animation(19)
        self.diff_fade_in = tex.get_animation(20)
        self.box_flicker = tex.get_animation(21)
        self.bounce_up_1 = tex.get_animation(22)
        self.bounce_down_1 = tex.get_animation(23)
        self.bounce_up_2 = tex.get_animation(24)
        self.bounce_down_2 = tex.get_animation(25)
        self.bg_resize.start()
        self.diff_fade_in.start()

    def update(self, current_ms):
        self.bg_resize.update(current_ms)
        self.diff_fade_in.update(current_ms)
        self.box_flicker.update(current_ms)
        self.bounce_up_1.update(current_ms)
        self.bounce_down_1.update(current_ms)
        self.bounce_up_2.update(current_ms)
        self.bounce_down_2.update(current_ms)

    def get_random_sort(self):
        diff = random.randint(0, 4)
        if diff == 0:
            level = random.randint(1, 5)
        elif diff == 1:
            level = random.randint(1, 7)
        elif diff == 2:
            level = random.randint(1, 8)
        elif diff == 3:
            level = random.randint(1, 10)
        else:
            level = random.choice([1, 5, 6, 7, 8, 9, 10])
        return diff, level

    def input_select(self):
        if self.confirmation:
            if self.confirm_index == 0:
                self.confirmation = False
                return None
            elif self.confirm_index == 1:
                return self.selected_box, self.selected_level
            elif self.confirm_index == 2:
                self.confirmation = False
                self.in_level_select = False
                return None
        elif self.in_level_select:
            self.confirmation = True
            self.bounce_up_1.start()
            self.bounce_down_1.start()
            self.bounce_up_2.start()
            self.bounce_down_2.start()
            self.confirm_index = 1
            return None
        if self.selected_box == -1:
            return (-1, -1)
        elif self.selected_box == 5:
            return (0, -1)
        elif self.selected_box == 4:
            return self.get_random_sort()
        self.in_level_select = True
        self.bg_resize.start()
        self.diff_fade_in.start()
        self.selected_level = min(self.selected_level, self.limits[self.selected_box])
        return None

    def input_left(self):
        if self.confirmation:
            self.confirm_index = max(self.confirm_index - 1, 0)
        elif self.in_level_select:
            self.selected_level = max(self.selected_level - 1, 1)
        else:
            self.selected_box = max(self.selected_box - 1, -1)

    def input_right(self):
        if self.confirmation:
            self.confirm_index = min(self.confirm_index + 1, 2)
        elif self.in_level_select:
            self.selected_level = min(self.selected_level + 1, self.limits[self.selected_box])
        else:
            self.selected_box = min(self.selected_box + 1, self.num_boxes - 1)

    def draw_diff_select(self):
        tex.draw_texture('diff_sort', 'background', scale=self.bg_resize.attribute, center=True)

        tex.draw_texture('diff_sort', 'back', fade=self.diff_fade_in.attribute)
        for i in range(self.num_boxes):
            if i == self.selected_box:
                tex.draw_texture('diff_sort', 'box_highlight', x=(100*i), fade=self.diff_fade_in.attribute)
                tex.draw_texture('diff_sort', 'box_text_highlight', x=(100*i), frame=i, fade=self.diff_fade_in.attribute)
            else:
                tex.draw_texture('diff_sort', 'box', x=(100*i), fade=self.diff_fade_in.attribute)
                tex.draw_texture('diff_sort', 'box_text', x=(100*i), frame=i, fade=self.diff_fade_in.attribute)
        if self.selected_box == -1:
            tex.draw_texture('diff_sort', 'back_outline', fade=self.box_flicker.attribute)
        else:
            tex.draw_texture('diff_sort', 'box_outline', x=(100*self.selected_box), fade=self.box_flicker.attribute)

        for i in range(self.num_boxes):
            if i < 4:
                tex.draw_texture('diff_sort', 'box_diff', x=(100*i), frame=i)

    def draw_level_select(self):
        tex.draw_texture('diff_sort', 'background', scale=self.bg_resize.attribute, center=True)
        if self.confirmation:
            tex.draw_texture('diff_sort', 'star_select_prompt')
        else:
            tex.draw_texture('diff_sort', 'star_select_text', fade=self.diff_fade_in.attribute)
        tex.draw_texture('diff_sort', 'star_limit', frame=self.selected_box, fade=self.diff_fade_in.attribute)
        tex.draw_texture('diff_sort', 'level_box', fade=self.diff_fade_in.attribute)
        tex.draw_texture('diff_sort', 'diff', frame=self.selected_box, fade=self.diff_fade_in.attribute)
        tex.draw_texture('diff_sort', 'star_num', frame=self.selected_level, fade=self.diff_fade_in.attribute)
        for i in range(self.selected_level):
            tex.draw_texture('diff_sort', 'star', x=(i*40.5), fade=self.diff_fade_in.attribute)

        if self.confirmation:
            texture = tex.textures['diff_sort']['level_box']
            ray.draw_rectangle(texture.x[0], texture.y[0], texture.x2[0], texture.y2[0], ray.fade(ray.BLACK, 0.5))
            y = -self.bounce_up_1.attribute + self.bounce_down_1.attribute - self.bounce_up_2.attribute + self.bounce_down_2.attribute
            for i in range(3):
                if i == self.confirm_index:
                    tex.draw_texture('diff_sort', 'small_box_highlight', x=(i*245), y=y)
                    tex.draw_texture('diff_sort', 'small_box_text_highlight', x=(i*245), y=y, frame=i)
                    tex.draw_texture('diff_sort', 'small_box_outline', x=(i*245), y=y, fade=self.box_flicker.attribute)
                else:
                    tex.draw_texture('diff_sort', 'small_box', x=(i*245), y=y)
                    tex.draw_texture('diff_sort', 'small_box_text', x=(i*245), y=y, frame=i)
        else:
            tex.draw_texture('diff_sort', 'pongos')

    def draw(self):
        ray.draw_rectangle(0, 0, 1280, 720, ray.fade(ray.BLACK, 0.6))
        if self.in_level_select:
            self.draw_level_select()
        else:
            self.draw_diff_select()

class NeiroSelector:
    def __init__(self):
        self.selected_sound = global_data.hit_sound
        with open(Path("Sounds") / 'hit_sounds' / 'neiro_list.txt', encoding='utf-8-sig') as neiro_list:
            self.sounds = neiro_list.readlines()
            self.sounds.append('無音')
        self.load_sound()
        self.is_finished = False
        self.is_confirmed = False
        self.move = tex.get_animation(28)
        self.move.start()
        self.blue_arrow_fade = tex.get_animation(29)
        self.blue_arrow_move = tex.get_animation(30)
        self.text = OutlinedText(self.sounds[self.selected_sound], 50, ray.WHITE, ray.BLACK)
        self.text_2 = OutlinedText(self.sounds[self.selected_sound], 50, ray.WHITE, ray.BLACK)
        self.move_sideways = tex.get_animation(31)
        self.fade_sideways = tex.get_animation(32)
        self.direction = -1

    def load_sound(self):
        if self.selected_sound == len(self.sounds):
            return
        if self.selected_sound == 0:
            self.curr_sound = audio.load_sound(Path("Sounds") / "hit_sounds" / str(self.selected_sound) / "don.wav")
        else:
            self.curr_sound = audio.load_sound(Path("Sounds") / "hit_sounds" / str(self.selected_sound) / "don.ogg")

    def move_left(self):
        self.selected_sound = (self.selected_sound - 1) % len(self.sounds)
        audio.unload_sound(self.curr_sound)
        self.load_sound()
        self.move_sideways.start()
        self.fade_sideways.start()
        self.text_2.unload()
        self.text_2 = OutlinedText(self.sounds[self.selected_sound], 50, ray.WHITE, ray.BLACK)
        self.direction = -1
        if self.selected_sound == len(self.sounds):
            return
        audio.play_sound(self.curr_sound)

    def move_right(self):
        self.selected_sound = (self.selected_sound + 1) % len(self.sounds)
        audio.unload_sound(self.curr_sound)
        self.load_sound()
        self.move_sideways.start()
        self.fade_sideways.start()
        self.text_2.unload()
        self.text_2 = OutlinedText(self.sounds[self.selected_sound], 50, ray.WHITE, ray.BLACK)
        self.direction = 1
        if self.selected_sound == len(self.sounds):
            return
        audio.play_sound(self.curr_sound)

    def confirm(self):
        if self.selected_sound == len(self.sounds):
            global_data.hit_sound = -1
        else:
            global_data.hit_sound = self.selected_sound
        self.is_confirmed = True
        self.move.restart()

    def update(self, current_ms):
        self.move.update(current_ms)
        self.blue_arrow_fade.update(current_ms)
        self.blue_arrow_move.update(current_ms)
        self.move_sideways.update(current_ms)
        self.fade_sideways.update(current_ms)
        if self.move_sideways.is_finished:
            self.text.unload()
            self.text = OutlinedText(self.sounds[self.selected_sound], 50, ray.WHITE, ray.BLACK)
        self.is_finished = self.move.is_finished and self.is_confirmed

    def draw(self):
        if self.is_confirmed:
            y = -370 + self.move.attribute
        else:
            y = -self.move.attribute
        tex.draw_texture('neiro', 'background', y=y)
        tex.draw_texture('neiro', f'{global_data.player_num}p', y=y)
        tex.draw_texture('neiro', 'divisor', y=y)
        tex.draw_texture('neiro', 'music_note', y=y, x=(self.move_sideways.attribute*self.direction), fade=self.fade_sideways.attribute)
        tex.draw_texture('neiro', 'music_note', y=y, x=(self.direction*-100) + (self.move_sideways.attribute*self.direction), fade=1 - self.fade_sideways.attribute)
        tex.draw_texture('neiro', 'blue_arrow', y=y, x=-self.blue_arrow_move.attribute, fade=self.blue_arrow_fade.attribute)
        tex.draw_texture('neiro', 'blue_arrow', y=y, x=200 + self.blue_arrow_move.attribute, mirror='horizontal', fade=self.blue_arrow_fade.attribute)

        counter = str(self.selected_sound+1)
        total_width = len(counter) * 20
        for i in range(len(counter)):
            tex.draw_texture('neiro', 'counter', frame=int(counter[i]), x=-(total_width // 2) + (i * 20), y=y)

        counter = str(len(self.sounds))
        total_width = len(counter) * 20
        for i in range(len(counter)):
            tex.draw_texture('neiro', 'counter', frame=int(counter[i]), x=-(total_width // 2) + (i * 20) + 60, y=y)

        dest = ray.Rectangle(235 - (self.text.texture.width//2) + (self.move_sideways.attribute*self.direction), y+1000, self.text.texture.width, self.text.texture.height)
        self.text.draw(self.text.default_src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, self.fade_sideways.attribute))

        dest = ray.Rectangle((self.direction*-100) + 235 - (self.text_2.texture.width//2) + (self.move_sideways.attribute*self.direction), y+1000, self.text_2.texture.width, self.text_2.texture.height)
        self.text_2.draw(self.text_2.default_src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, 1 - self.fade_sideways.attribute))

class ModifierSelector:
    TEX_MAP = {
        "auto": "mod_auto",
        "speed": "mod_baisaku",
        "display": "mod_doron",
        "inverse": "mod_abekobe",
        "random": "mod_kimagure"
    }
    NAME_MAP = {
        "auto": "オート",
        "speed": "はやさ",
        "display": "ドロン",
        "inverse": "あべこべ",
        "random": "ランダム"
    }
    def __init__(self):
        self.mods = fields(Modifiers)
        self.current_mod_index = 0
        self.is_confirmed = False
        self.is_finished = False
        self.blue_arrow_fade = tex.get_animation(29)
        self.blue_arrow_move = tex.get_animation(30)
        self.move = tex.get_animation(28)
        self.move.start()
        self.move_sideways = tex.get_animation(31)
        self.fade_sideways = tex.get_animation(32)
        self.direction = -1
        self.text_name = [OutlinedText(ModifierSelector.NAME_MAP[mod.name], 30, ray.WHITE, ray.BLACK, outline_thickness=3.5) for mod in self.mods]
        self.text_true = OutlinedText('する', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_false = OutlinedText('しない', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_speed = OutlinedText(str(global_data.modifiers.speed), 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_kimagure = OutlinedText('きまぐれ', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_detarame = OutlinedText('でたらめ', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)

        # Secondary text objects for animation
        self.text_true_2 = OutlinedText('する', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_false_2 = OutlinedText('しない', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_speed_2 = OutlinedText(str(global_data.modifiers.speed), 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_kimagure_2 = OutlinedText('きまぐれ', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)
        self.text_detarame_2 = OutlinedText('でたらめ', 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)

    def update(self, current_ms):
        self.is_finished = self.is_confirmed and self.move.is_finished
        if self.is_finished:
            for text in self.text_name:
                text.unload()
        self.move.update(current_ms)
        self.blue_arrow_fade.update(current_ms)
        self.blue_arrow_move.update(current_ms)
        self.move_sideways.update(current_ms)
        self.fade_sideways.update(current_ms)
        if self.move_sideways.is_finished and not self.is_confirmed:
            current_mod = self.mods[self.current_mod_index]
            current_value = getattr(global_data.modifiers, current_mod.name)

            if current_mod.name == 'speed':
                self.text_speed.unload()
                self.text_speed = OutlinedText(str(current_value), 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)

    def confirm(self):
        if self.is_confirmed:
            return
        self.current_mod_index += 1
        if self.current_mod_index == len(self.mods):
            self.is_confirmed = True
            self.move.restart()

    def _start_text_animation(self, direction):
        self.move_sideways.start()
        self.fade_sideways.start()
        self.direction = direction

        # Update secondary text objects for the new values
        current_mod = self.mods[self.current_mod_index]
        current_value = getattr(global_data.modifiers, current_mod.name)

        if current_mod.name == 'speed':
            self.text_speed_2.unload()
            self.text_speed_2 = OutlinedText(str(current_value), 30, ray.WHITE, ray.BLACK, outline_thickness=3.5)

    def left(self):
        if self.is_confirmed:
            return
        current_mod = self.mods[self.current_mod_index]
        current_value = getattr(global_data.modifiers, current_mod.name)
        if current_mod.type is bool:
            setattr(global_data.modifiers, current_mod.name, not current_value)
            self._start_text_animation(-1)
        elif current_mod.name == 'speed':
            setattr(global_data.modifiers, current_mod.name, max(0.1, (current_value*10 - 1))/10)
            self._start_text_animation(-1)
        elif current_mod.name == 'random':
            setattr(global_data.modifiers, current_mod.name, max(0, current_value-1))
            self._start_text_animation(-1)

    def right(self):
        if self.is_confirmed:
            return
        current_mod = self.mods[self.current_mod_index]
        current_value = getattr(global_data.modifiers, current_mod.name)
        if current_mod.type is bool:
            setattr(global_data.modifiers, current_mod.name, not current_value)
            self._start_text_animation(1)
        elif current_mod.name == 'speed':
            setattr(global_data.modifiers, current_mod.name, (current_value*10 + 1)/10)
            self._start_text_animation(1)
        elif current_mod.name == 'random':
            setattr(global_data.modifiers, current_mod.name, (current_value+1) % 3)
            self._start_text_animation(1)

    def _draw_animated_text(self, text_primary, text_secondary, x, y, should_animate):
        if should_animate and not self.move_sideways.is_finished:
            # Draw primary text moving out
            dest = ray.Rectangle(x + (self.move_sideways.attribute * self.direction), y,
                               text_primary.texture.width, text_primary.texture.height)
            text_primary.draw(text_primary.default_src, dest, ray.Vector2(0, 0), 0,
                            ray.fade(ray.WHITE, self.fade_sideways.attribute))

            # Draw secondary text moving in
            dest = ray.Rectangle((self.direction * -100) + x + (self.move_sideways.attribute * self.direction), y,
                               text_secondary.texture.width, text_secondary.texture.height)
            text_secondary.draw(text_secondary.default_src, dest, ray.Vector2(0, 0), 0,
                              ray.fade(ray.WHITE, 1 - self.fade_sideways.attribute))
        else:
            # Draw static text
            dest = ray.Rectangle(x, y, text_primary.texture.width, text_primary.texture.height)
            text_primary.draw(text_primary.default_src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

    def draw(self):
        if self.is_confirmed:
            move = self.move.attribute - 370
        else:
            move = -self.move.attribute
        tex.draw_texture('modifier', 'top', y=move)
        tex.draw_texture('modifier', f'{global_data.player_num}p', y=move)
        tex.draw_texture('modifier', 'bottom', y=move + (len(self.mods)*50))

        for i in range(len(self.mods)):
            tex.draw_texture('modifier', 'background', y=move + (i*50))
            if i == self.current_mod_index:
                tex.draw_texture('modifier', 'mod_bg_highlight', y=move + (i*50))
            else:
                tex.draw_texture('modifier', 'mod_bg', y=move + (i*50))
            tex.draw_texture('modifier', 'mod_box', y=move + (i*50))
            dest = ray.Rectangle(92, 819 + move + (i*50), self.text_name[i].texture.width, self.text_name[i].texture.height)
            self.text_name[i].draw(self.text_name[i].default_src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

            current_mod = self.mods[i]
            current_value = getattr(global_data.modifiers, current_mod.name)
            is_current_mod = (i == self.current_mod_index)

            if current_mod.type is bool:
                if current_value:
                    tex.draw_texture('modifier', ModifierSelector.TEX_MAP[self.mods[i].name], y=move + (i*50))
                    x = 330 - (self.text_true.texture.width//2)
                    y = 819 + move + (i*50)
                    self._draw_animated_text(self.text_true, self.text_true_2, x, y, is_current_mod)
                else:
                    x = 330 - (self.text_false.texture.width//2)
                    y = 819 + move + (i*50)
                    self._draw_animated_text(self.text_false, self.text_false_2, x, y, is_current_mod)
            elif current_mod.name == 'speed':
                x = 330 - (self.text_speed.texture.width//2)
                y = 819 + move + (i*50)
                self._draw_animated_text(self.text_speed, self.text_speed_2, x, y, is_current_mod)

                if current_value >= 4.0:
                    tex.draw_texture('modifier', 'mod_yonbai', y=move + (i*50))
                elif current_value >= 3.0:
                    tex.draw_texture('modifier', 'mod_sanbai', y=move + (i*50))
                elif current_value > 1.0:
                    tex.draw_texture('modifier', ModifierSelector.TEX_MAP[self.mods[i].name], y=move + (i*50))
            elif current_mod.name == 'random':
                if current_value == 1:
                    x = 330 - (self.text_kimagure.texture.width//2)
                    y = 819 + move + (i*50)
                    self._draw_animated_text(self.text_kimagure, self.text_kimagure_2, x, y, is_current_mod)
                    tex.draw_texture('modifier', ModifierSelector.TEX_MAP[self.mods[i].name], y=move + (i*50))
                elif current_value == 2:
                    x = 330 - (self.text_detarame.texture.width//2)
                    y = 819 + move + (i*50)
                    self._draw_animated_text(self.text_detarame, self.text_detarame_2, x, y, is_current_mod)
                    tex.draw_texture('modifier', 'mod_detarame', y=move + (i*50))
                else:
                    x = 330 - (self.text_false.texture.width//2)
                    y = 819 + move + (i*50)
                    self._draw_animated_text(self.text_false, self.text_false_2, x, y, is_current_mod)

            if i == self.current_mod_index:
                tex.draw_texture('modifier', 'blue_arrow', y=move + (i*50), x=-self.blue_arrow_move.attribute, fade=self.blue_arrow_fade.attribute)
                tex.draw_texture('modifier', 'blue_arrow', y=move + (i*50), x=110 + self.blue_arrow_move.attribute, mirror='horizontal', fade=self.blue_arrow_fade.attribute)

class ScoreHistory:
    def __init__(self, scores: dict[int, tuple[int, int, int, int]], current_ms):
        self.scores = {k: v for k, v in scores.items() if v is not None}
        self.difficulty_keys = list(self.scores.keys())
        self.curr_difficulty_index = 0
        self.curr_difficulty_index = (self.curr_difficulty_index + 1) % len(self.difficulty_keys)
        self.curr_difficulty = self.difficulty_keys[self.curr_difficulty_index]
        self.curr_score = self.scores[self.curr_difficulty][0]
        self.curr_score_su = self.scores[self.curr_difficulty][0]
        self.last_ms = current_ms

    def update(self, current_ms):
        if current_ms >= self.last_ms + 1000:
            self.last_ms = current_ms
            self.curr_difficulty_index = (self.curr_difficulty_index + 1) % len(self.difficulty_keys)
            self.curr_difficulty = self.difficulty_keys[self.curr_difficulty_index]
            self.curr_score = self.scores[self.curr_difficulty][0]
            self.curr_score_su = self.scores[self.curr_difficulty][0]

    def draw(self):
        tex.draw_texture('leaderboard','background')
        tex.draw_texture('leaderboard','title')

        if self.curr_difficulty == 4:
            tex.draw_texture('leaderboard', 'normal_ura')
            tex.draw_texture('leaderboard', 'shinuchi_ura')
        else:
            tex.draw_texture('leaderboard', 'normal')
            tex.draw_texture('leaderboard', 'shinuchi')

        color = ray.BLACK
        if self.curr_difficulty == 4:
            color = ray.WHITE
            tex.draw_texture('leaderboard','ura')

        tex.draw_texture('leaderboard', 'pts', color=color)
        tex.draw_texture('leaderboard', 'pts', y=50)

        tex.draw_texture('leaderboard', 'difficulty', frame=self.curr_difficulty)

        counter = str(self.curr_score)
        total_width = len(counter) * 14
        for i in range(len(counter)):
            tex.draw_texture('leaderboard', 'counter', frame=int(counter[i]), x=-(total_width // 2) + (i * 14), color=color)

        counter = str(self.curr_score_su)
        total_width = len(counter) * 14
        for i in range(len(counter)):
            tex.draw_texture('leaderboard', 'counter', frame=int(counter[i]), x=-(total_width // 2) + (i * 14), y=50, color=ray.WHITE)

class FileSystemItem:
    GENRE_MAP = {
        'J-POP': 1,
        'アニメ': 2,
        'VOCALOID': 3,
        'どうよう': 4,
        'バラエティー': 5,
        'クラシック': 6,
        'ゲームミュージック': 7,
        'ナムコオリジナル': 8,
        'RECOMMENDED': 10,
        'FAVORITE': 11,
        'RECENT': 12,
        '段位道場': 13,
        'DIFFICULTY': 14
    }
    GENRE_MAP_2 = {
        'ボーカロイド': 3,
        'バラエティ': 5
    }
    """Base class for files and directories in the navigation system"""
    def __init__(self, path: Path, name: str):
        self.path = path
        self.name = name

class Directory(FileSystemItem):
    """Represents a directory in the navigation system"""
    COLLECTIONS = [
        'NEW',
        'RECENT',
        'FAVORITE',
        'DIFFICULTY',
        'RECOMMENDED'
    ]
    def __init__(self, path: Path, name: str, texture_index: int, has_box_def=False, to_root=False, back=False, tja_count=0, box_texture=None, collection=None):
        super().__init__(path, name)
        self.has_box_def = has_box_def
        self.to_root = to_root
        self.back = back
        self.tja_count = tja_count
        self.collection = None
        if collection in Directory.COLLECTIONS:
            self.collection = collection
        if collection in FileSystemItem.GENRE_MAP:
            texture_index = FileSystemItem.GENRE_MAP[collection]
        elif self.to_root or self.back:
            texture_index = SongBox.BACK_INDEX

        self.box = SongBox(name, texture_index, True, tja_count=tja_count, box_texture=box_texture)

class SongFile(FileSystemItem):
    """Represents a song file (TJA) in the navigation system"""
    def __init__(self, path: Path, name: str, texture_index: int, tja=None, name_texture_index: Optional[int]=None):
        super().__init__(path, name)
        self.is_recent = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)) <= timedelta(days=7)
        self.tja = tja or TJAParser(path)
        if self.is_recent:
            self.tja.ex_data.new = True
        title = self.tja.metadata.title.get(global_data.config['general']['language'].lower(), self.tja.metadata.title['en'])
        self.hash = global_data.song_paths[path]
        self.box = SongBox(title, texture_index, False, tja=self.tja, name_texture_index=name_texture_index if name_texture_index is not None else texture_index)
        self.box.hash = global_data.song_hashes[self.hash][0]["diff_hashes"]
        self.box.get_scores()

class FileNavigator:
    """Manages navigation through pre-generated Directory and SongFile objects"""
    def __init__(self, root_dirs: list[str]):
        self.root_dirs = [Path(p) if not isinstance(p, Path) else p for p in root_dirs]

        # Pre-generated objects storage
        self.all_directories: dict[str, Directory] = {}  # path -> Directory
        self.all_song_files: dict[str, SongFile] = {}    # path -> SongFile
        self.directory_contents: dict[str, list[Union[Directory, SongFile]]] = {}  # path -> list of items

        # OPTION 2: Lazy crown calculation with caching
        self.directory_crowns: dict[str, dict] = dict()  # path -> crown list
        self.crown_cache_dirty: set[str] = set()  # directories that need crown recalculation

        # Navigation state - simplified without root-specific state
        self.current_dir = Path()  # Empty path represents virtual root
        self.items: list[Directory | SongFile] = []
        self.new_items: list[Directory | SongFile] = []
        self.favorite_folder: Optional[Directory] = None
        self.recent_folder: Optional[Directory] = None
        self.selected_index = 0
        self.diff_sort_diff = 4
        self.diff_sort_level = 10
        self.history = []
        self.box_open = False
        self.genre_bg = None
        self.song_count = 0

        # Generate all objects upfront
        self._generate_all_objects()
        self._create_virtual_root()
        self.load_current_directory()

    def _create_virtual_root(self):
        """Create a virtual root directory containing all root directories"""
        virtual_root_items = []

        for root_path in self.root_dirs:
            if not root_path.exists():
                continue

            root_key = str(root_path)
            if root_key in self.all_directories:
                # Root has box.def, add the directory itself
                virtual_root_items.append(self.all_directories[root_key])
            else:
                # Root doesn't have box.def, add its immediate children with box.def
                for child_path in sorted(root_path.iterdir()):
                    if child_path.is_dir():
                        child_key = str(child_path)
                        if child_key in self.all_directories:
                            virtual_root_items.append(self.all_directories[child_key])

                # Also add direct TJA files from root
                all_tja_files = self._find_tja_files_recursive(root_path)
                for tja_path in sorted(all_tja_files):
                    song_key = str(tja_path)
                    if song_key in self.all_song_files:
                        virtual_root_items.append(self.all_song_files[song_key])

        # Store virtual root contents (empty path key represents root)
        self.directory_contents["."] = virtual_root_items

    def _generate_all_objects(self):
        """Generate all Directory and SongFile objects in advance"""
        print("Generating all Directory and SongFile objects...")

        # Generate objects for each root directory
        for root_path in self.root_dirs:
            if not root_path.exists():
                print(f"Root directory does not exist: {root_path}")
                continue

            self._generate_objects_recursive(root_path)

        print(f"Object generation complete. "
                    f"Directories: {len(self.all_directories)}, "
                    f"Songs: {len(self.all_song_files)}")

    def _generate_objects_recursive(self, dir_path: Path):
        """Recursively generate Directory and SongFile objects for a directory"""
        if not dir_path.is_dir():
            return

        dir_key = str(dir_path)

        # Check for box.def
        has_box_def = (dir_path / "box.def").exists()

        # Only create Directory objects for directories with box.def
        if has_box_def:
            # Parse box.def if it exists
            name = dir_path.name if dir_path.name else str(dir_path)
            texture_index = SongBox.DEFAULT_INDEX
            box_texture = None
            collection = None

            name, texture_index, collection = self._parse_box_def(dir_path)
            box_png_path = dir_path / "box.png"
            if box_png_path.exists():
                box_texture = str(box_png_path)

            # Count TJA files for this directory
            tja_count = self._count_tja_files(dir_path)
            if collection == Directory.COLLECTIONS[4]:
                tja_count = 10
            elif collection == Directory.COLLECTIONS[0]:
                tja_count = len(self.new_items)

            # Create Directory object
            directory_obj = Directory(
                dir_path, name, texture_index,
                has_box_def=has_box_def,
                tja_count=tja_count,
                box_texture=box_texture,
                collection=collection
            )
            if directory_obj.collection == Directory.COLLECTIONS[2]:
                self.favorite_folder = directory_obj
            elif directory_obj.collection == Directory.COLLECTIONS[1]:
                self.recent_folder = directory_obj
            self.all_directories[dir_key] = directory_obj

            # Generate content list for this directory
            content_items = []

            # Add child directories that have box.def
            child_dirs = []
            for item_path in dir_path.iterdir():
                if item_path.is_dir():
                    child_has_box_def = (item_path / "box.def").exists()
                    if child_has_box_def:
                        child_dirs.append(item_path)
                        # Recursively generate objects for child directory
                        self._generate_objects_recursive(item_path)

            # Sort and add child directories
            for child_path in sorted(child_dirs):
                child_key = str(child_path)
                if child_key in self.all_directories:
                    content_items.append(self.all_directories[child_key])

            # Get TJA files for this directory
            tja_files = self._get_tja_files_for_directory(dir_path)

            # Create SongFile objects
            for tja_path in sorted(tja_files):
                song_key = str(tja_path)
                if song_key not in self.all_song_files:
                    song_obj = SongFile(tja_path, tja_path.name, texture_index)
                    self.song_count += 1
                    global_data.song_progress = self.song_count / global_data.total_songs
                    if song_obj.is_recent:
                        self.new_items.append(SongFile(tja_path, tja_path.name, SongBox.DEFAULT_INDEX, name_texture_index=texture_index))
                    self.all_song_files[song_key] = song_obj

                content_items.append(self.all_song_files[song_key])

            # Store content for this directory
            self.directory_contents[dir_key] = content_items

            # OPTION 2: Mark directory for lazy crown calculation
            self.crown_cache_dirty.add(dir_key)

        else:
            # For directories without box.def, still process their children
            for item_path in dir_path.iterdir():
                if item_path.is_dir():
                    self._generate_objects_recursive(item_path)

            # Create SongFile objects for TJA files in non-boxed directories
            tja_files = self._find_tja_files_in_directory_only(dir_path)
            for tja_path in tja_files:
                song_key = str(tja_path)
                if song_key not in self.all_song_files:
                    try:
                        song_obj = SongFile(tja_path, tja_path.name, SongBox.DEFAULT_INDEX)
                        self.song_count += 1
                        global_data.song_progress = self.song_count / global_data.total_songs
                        self.all_song_files[song_key] = song_obj
                    except Exception as e:
                        print(f"Error creating SongFile for {tja_path}: {e}")
                        continue

    def is_at_root(self) -> bool:
        """Check if currently at the virtual root"""
        return self.current_dir == Path()

    def load_current_directory(self, selected_item: Optional[Directory] = None):
        """Load pre-generated items for the current directory (unified for root and subdirs)"""
        dir_key = str(self.current_dir)

        # Determine if current directory has child directories with box.def
        has_children = False
        if self.is_at_root():
            has_children = True  # Root always has "children" (the root directories)
        else:
            has_children = any(item.is_dir() and (item / "box.def").exists()
                             for item in self.current_dir.iterdir())

        self.genre_bg = None
        self.in_favorites = False

        if has_children:
            self.items = []
            if not self.box_open:
                self.selected_index = 0

        start_box = None
        end_box = None

        # Add back navigation item (only if not at root)
        if not self.is_at_root():
            back_dir = Directory(self.current_dir.parent, "", SongBox.BACK_INDEX, back=True)
            if not has_children:
                start_box = back_dir.box
            self.items.insert(self.selected_index, back_dir)

        # Add pre-generated content for this directory
        if dir_key in self.directory_contents:
            content_items = self.directory_contents[dir_key]

            # Handle special collections (same logic as before)
            if isinstance(selected_item, Directory):
                if selected_item.collection == Directory.COLLECTIONS[0]:
                    content_items = self.new_items
                elif selected_item.collection == Directory.COLLECTIONS[1]:
                    if self.recent_folder is None:
                        raise Exception("tried to enter recent folder without recents")
                    self._generate_objects_recursive(self.recent_folder.path)
                    selected_item.box.tja_count_text = None
                    selected_item.box.tja_count = self._count_tja_files(self.recent_folder.path)
                    content_items = self.directory_contents[dir_key]
                elif selected_item.collection == Directory.COLLECTIONS[2]:
                    if self.favorite_folder is None:
                        raise Exception("tried to enter favorite folder without favorites")
                    self._generate_objects_recursive(self.favorite_folder.path)
                    tja_files = self._get_tja_files_for_directory(self.favorite_folder.path)
                    self._calculate_directory_crowns(dir_key, tja_files)
                    selected_item.box.tja_count_text = None
                    selected_item.box.tja_count = self._count_tja_files(self.favorite_folder.path)
                    content_items = self.directory_contents[dir_key]
                    self.in_favorites = True
                elif selected_item.collection == Directory.COLLECTIONS[3]:
                    content_items = []
                    parent_dir = selected_item.path.parent
                    for sibling_path in parent_dir.iterdir():
                        if sibling_path.is_dir() and sibling_path != selected_item.path:
                            sibling_key = str(sibling_path)
                            if sibling_key in self.directory_contents:
                                for item in self.directory_contents[sibling_key]:
                                    if isinstance(item, SongFile) and item:
                                        if self.diff_sort_diff in item.tja.metadata.course_data and item.tja.metadata.course_data[self.diff_sort_diff].level == self.diff_sort_level:
                                            if item not in content_items:
                                                content_items.append(item)
                elif selected_item.collection == Directory.COLLECTIONS[4]:
                    parent_dir = selected_item.path.parent
                    temp_items = []
                    for sibling_path in parent_dir.iterdir():
                        if sibling_path.is_dir() and sibling_path != selected_item.path:
                            sibling_key = str(sibling_path)
                            if sibling_key in self.directory_contents:
                                for item in self.directory_contents[sibling_key]:
                                    temp_items.append(item)
                    content_items = random.sample(temp_items, 10)

            if content_items == [] or (selected_item is not None and selected_item.box.texture_index == 13):
                self.go_back()
                return
            i = 1
            for item in content_items:
                if isinstance(item, SongFile):
                    if i % 10 == 0 and i != 0:
                        back_dir = Directory(self.current_dir.parent, "", SongBox.BACK_INDEX, back=True)
                        self.items.insert(self.selected_index+i, back_dir)
                        i += 1
                if not has_children:
                    if selected_item is not None:
                        item.box.texture_index = selected_item.box.texture_index
                    self.items.insert(self.selected_index+i, item)
                else:
                    self.items.append(item)
                i += 1

            if not has_children:
                self.box_open = True
                end_box = content_items[-1].box
                if selected_item in self.items:
                    self.items.remove(selected_item)

        # Calculate crowns for directories
        for item in self.items:
            if isinstance(item, Directory):
                item_key = str(item.path)
                if item_key in self.directory_contents:  # Only for real directories
                    item.box.crown = self._get_directory_crowns_cached(item_key)
                else:
                    # Navigation items (back/to_root)
                    item.box.crown = dict()

        self.calculate_box_positions()

        if (not has_children and start_box is not None
            and end_box is not None and selected_item is not None
            and selected_item.box.hori_name is not None):
            hori_name = selected_item.box.hori_name
            diff_sort = None
            if selected_item.collection == Directory.COLLECTIONS[3]:
                diff_sort = self.diff_sort_level
                diffs = ['かんたん', 'ふつう', 'むずかしい', 'おに']
                hori_name = OutlinedText(diffs[min(3, self.diff_sort_diff)], 40, ray.WHITE, ray.BLACK, outline_thickness=5)
            self.genre_bg = GenreBG(start_box, end_box, hori_name, diff_sort)

    def select_current_item(self):
        """Select the currently highlighted item"""
        if not self.items or self.selected_index >= len(self.items):
            return

        selected_item = self.items[self.selected_index]

        if isinstance(selected_item, Directory):
            if self.box_open:
                self.go_back()
                return

            if selected_item.back:
                # Handle back navigation
                if self.current_dir.parent == Path():
                    # Going back to root
                    self.current_dir = Path()
                else:
                    self.current_dir = self.current_dir.parent
            else:
                # Save current state to history
                self.history.append((self.current_dir, self.selected_index))
                self.current_dir = selected_item.path

            self.load_current_directory(selected_item=selected_item)

        elif isinstance(selected_item, SongFile):
            return selected_item

    def go_back(self):
        """Navigate back to the previous directory"""
        if self.history:
            previous_dir, previous_index = self.history.pop()
            self.current_dir = previous_dir
            self.selected_index = previous_index
            self.load_current_directory()
            self.box_open = False

    # ... (rest of the methods remain the same: navigate_left, navigate_right, etc.)

    def _count_tja_files(self, folder_path: Path):
        """Count TJA files in directory"""
        tja_count = 0

        # Find all song_list.txt files recursively
        song_list_files = list(folder_path.rglob("song_list.txt"))

        if song_list_files:
            # Process all song_list.txt files found
            for song_list_path in song_list_files:
                with open(song_list_path, 'r', encoding='utf-8-sig') as song_list_file:
                    tja_count += len([line for line in song_list_file.readlines() if line.strip()])
        # Fallback: Use recursive counting of .tja files
        tja_count += sum(1 for _ in folder_path.rglob("*.tja"))

        return tja_count

    def _get_directory_crowns_cached(self, dir_key: str) -> dict:
        """Get crowns for a directory, calculating only if needed"""
        if dir_key in self.crown_cache_dirty or dir_key not in self.directory_crowns:
            # Calculate crowns on-demand
            dir_path = Path(dir_key)
            tja_files = self._get_tja_files_for_directory(dir_path)
            self._calculate_directory_crowns(dir_key, tja_files)
            self.crown_cache_dirty.discard(dir_key)

        return self.directory_crowns.get(dir_key, dict())

    def _calculate_directory_crowns(self, dir_key: str, tja_files: list):
        """Pre-calculate crowns for a directory"""
        all_scores = dict()
        crowns = dict()

        for tja_path in tja_files:
            song_key = str(tja_path)
            if song_key in self.all_song_files:
                song_obj = self.all_song_files[song_key]
                for diff in song_obj.box.scores:
                    if diff not in all_scores:
                        all_scores[diff] = []
                    all_scores[diff].append(song_obj.box.scores[diff])

        for diff in all_scores:
            if all(score is not None and score[3] == 0 for score in all_scores[diff]):
                crowns[diff] = 'FC'
            elif all(score is not None and score[4] == 1 for score in all_scores[diff]):
                crowns[diff] = 'CLEAR'

        self.directory_crowns[dir_key] = crowns

    def _get_tja_files_for_directory(self, directory: Path):
        """Get TJA files for a specific directory"""
        if (directory / 'song_list.txt').exists():
            return self._read_song_list(directory)
        else:
            return self._find_tja_files_in_directory_only(directory)

    def _find_tja_files_in_directory_only(self, directory: Path):
        """Find TJA files only in the specified directory, not recursively in subdirectories with box.def"""
        tja_files: list[Path] = []

        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() == ".tja":
                tja_files.append(path)
            elif path.is_dir():
                # Only recurse into subdirectories that don't have box.def
                sub_dir_has_box_def = (path / "box.def").exists()
                if not sub_dir_has_box_def:
                    tja_files.extend(self._find_tja_files_in_directory_only(path))

        return tja_files

    def _find_tja_files_recursive(self, directory: Path, box_def_dirs_only=True):
        tja_files: list[Path] = []

        has_box_def = (directory / "box.def").exists()
        if box_def_dirs_only and has_box_def and directory != self.current_dir:
            return []

        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() == ".tja":
                tja_files.append(path)
            elif path.is_dir():
                sub_dir_has_box_def = (path / "box.def").exists()
                if not sub_dir_has_box_def:
                    tja_files.extend(self._find_tja_files_recursive(path, box_def_dirs_only))

        return tja_files

    def _parse_box_def(self, path: Path):
        """Parse box.def file for directory metadata"""
        texture_index = SongBox.DEFAULT_INDEX
        name = path.name
        collection = None
        encoding = test_encodings(path / "box.def")

        try:
            with open(path / "box.def", 'r', encoding=encoding) as box_def:
                for line in box_def:
                    line = line.strip()
                    if line.startswith("#GENRE:"):
                        genre = line.split(":", 1)[1].strip()
                        texture_index = FileSystemItem.GENRE_MAP.get(genre, SongBox.DEFAULT_INDEX)
                        if texture_index == SongBox.DEFAULT_INDEX:
                            texture_index = FileSystemItem.GENRE_MAP_2.get(genre, SongBox.DEFAULT_INDEX)
                    elif line.startswith("#TITLE:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("#TITLEJA:"):
                        if global_data.config['general']['language'] == 'ja':
                            name = line.split(":", 1)[1].strip()
                    elif line.startswith("#COLLECTION"):
                        collection = line.split(":", 1)[1].strip()
        except Exception as e:
            print(f"Error parsing box.def in {path}: {e}")

        return name, texture_index, collection

    def _read_song_list(self, path: Path):
        """Read and process song_list.txt file"""
        tja_files: list[Path] = []
        updated_lines = []
        file_updated = False
        with open(path / 'song_list.txt', 'r', encoding='utf-8-sig') as song_list:
            for line in song_list:
                line = line.strip()
                if not line:
                    continue

                parts = line.split('|')
                if len(parts) < 3:
                    continue

                hash_val, title, subtitle = parts[0], parts[1], parts[2]
                original_hash = hash_val

                if hash_val in global_data.song_hashes:
                    file_path = Path(global_data.song_hashes[hash_val][0]["file_path"])
                    if file_path.exists() and file_path not in tja_files:
                        tja_files.append(file_path)
                else:
                    # Try to find by title and subtitle
                    for key, value in global_data.song_hashes.items():
                        for i in range(len(value)):
                            song = value[i]
                            if (song["title"]["en"] == title and
                                song["subtitle"]["en"] == subtitle and
                                Path(song["file_path"]).exists()):
                                hash_val = key
                                tja_files.append(Path(global_data.song_hashes[hash_val][i]["file_path"]))
                                break

                if hash_val != original_hash:
                    file_updated = True
                updated_lines.append(f"{hash_val}|{title}|{subtitle}")

        # Write back updated song list if needed
        if file_updated:
            with open(path / 'song_list.txt', 'w', encoding='utf-8-sig') as song_list:
                for line in updated_lines:
                    print("updated", line)
                    song_list.write(line + '\n')

        return tja_files

    def calculate_box_positions(self):
        """Dynamically calculate box positions based on current selection with wrap-around support"""
        if not self.items:
            return

        for i, item in enumerate(self.items):
            offset = i - self.selected_index

            if offset > len(self.items) // 2:
                offset -= len(self.items)
            elif offset < -len(self.items) // 2:
                offset += len(self.items)

            position = SongSelectScreen.BOX_CENTER + (100 * offset)
            if position == SongSelectScreen.BOX_CENTER:
                position += 150
            elif position > SongSelectScreen.BOX_CENTER:
                position += 300
            else:
                position -= 0

            if item.box.position == -11111:
                item.box.position = position
                item.box.target_position = position
            else:
                item.box.target_position = position

    def mark_crowns_dirty_for_song(self, song_file: SongFile):
        """Mark directories as needing crown recalculation when a song's score changes"""
        song_path = song_file.path

        # Find all directories that contain this song and mark them as dirty
        for dir_key, content_items in self.directory_contents.items():
            for item in content_items:
                if isinstance(item, SongFile) and item.path == song_path:
                    self.crown_cache_dirty.add(dir_key)
                    break

    def navigate_left(self):
        """Move selection left with wrap-around"""
        if self.items:
            self.selected_index = (self.selected_index - 1) % len(self.items)
            self.calculate_box_positions()

    def navigate_right(self):
        """Move selection right with wrap-around"""
        if self.items:
            self.selected_index = (self.selected_index + 1) % len(self.items)
            self.calculate_box_positions()

    def get_current_item(self):
        """Get the currently selected item"""
        if self.items and 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        raise Exception("No current item available")

    def reset_items(self):
        for item in self.items:
            item.box.reset()

    def add_recent(self):
        song = self.get_current_item()
        if isinstance(song, Directory):
            return
        if self.recent_folder is None:
            return

        recents_path = self.recent_folder.path / 'song_list.txt'
        new_entry = f'{song.hash}|{song.tja.metadata.title["en"]}|{song.tja.metadata.subtitle["en"]}\n'
        existing_entries = []
        if recents_path.exists():
            with open(recents_path, 'r', encoding='utf-8-sig') as song_list:
                existing_entries = song_list.readlines()
        existing_entries = [entry for entry in existing_entries if not entry.startswith(f'{song.hash}|')]
        all_entries = [new_entry] + existing_entries
        recent_entries = all_entries[:25]
        with open(recents_path, 'w', encoding='utf-8-sig') as song_list:
            song_list.writelines(recent_entries)

        print("Added recent: ", song.hash, song.tja.metadata.title['en'], song.tja.metadata.subtitle['en'])

    def add_favorite(self) -> bool:
        song = self.get_current_item()
        if isinstance(song, Directory):
            return False
        if self.favorite_folder is None:
            return False
        favorites_path = self.favorite_folder.path / 'song_list.txt'
        lines = []
        with open(favorites_path, 'r', encoding='utf-8-sig') as song_list:
            for line in song_list:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                hash, title, subtitle = line.split('|')
                if song.hash == hash or (song.tja.metadata.title['en'] == title and song.tja.metadata.subtitle['en'] == subtitle):
                    if not self.in_favorites:
                        return False
                else:
                    lines.append(line)
        if self.in_favorites:
            with open(favorites_path, 'w', encoding='utf-8-sig') as song_list:
                for line in lines:
                    song_list.write(line + '\n')
            print("Removed favorite:", song.hash, song.tja.metadata.title['en'], song.tja.metadata.subtitle['en'])
        else:
            with open(favorites_path, 'a', encoding='utf-8-sig') as song_list:
                song_list.write(f'{song.hash}|{song.tja.metadata.title['en']}|{song.tja.metadata.subtitle['en']}\n')
            print("Added favorite: ", song.hash, song.tja.metadata.title['en'], song.tja.metadata.subtitle['en'])
        return True
