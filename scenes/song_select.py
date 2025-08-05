import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import pyray as ray

from libs.animation import Animation, MoveAnimation
from libs.audio import audio
from libs.texture import tex
from libs.tja import TJAParser
from libs.transition import Transition
from libs.utils import (
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

class SongSelectScreen:
    BOX_CENTER = 444
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_init = False
        self.root_dir = global_data.config["paths"]["tja_path"]
        self.screen_width = screen_width
        self.screen_height = screen_height

    def load_navigator(self):
        self.navigator = FileNavigator(self.root_dir)

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(sounds_dir / "inst_00_don.wav")
        self.sound_kat = audio.load_sound(sounds_dir / "inst_00_katsu.wav")
        self.sound_skip = audio.load_sound(sounds_dir / 'song_select' / 'Skip.ogg')
        self.sound_ura_switch = audio.load_sound(sounds_dir / 'song_select' / 'SE_SELECT [4].ogg')
        audio.set_sound_volume(self.sound_ura_switch, 0.25)
        self.sound_bgm = audio.load_sound(sounds_dir / "song_select" / "JINGLE_GENRE [1].ogg")

    def on_screen_start(self):
        if not self.screen_init:
            tex.load_screen_textures('song_select')
            self.load_sounds()
            self.selected_song = None
            self.selected_difficulty = -1
            self.background_move = tex.get_animation(0)
            self.background_move.start()
            self.move_away = tex.get_animation(1)
            self.diff_fade_out = tex.get_animation(2)
            self.state = State.BROWSING
            self.text_fade_out = tex.get_animation(3)
            self.text_fade_in = tex.get_animation(4)
            self.background_fade_change = tex.get_animation(5)
            self.game_transition = None
            self.texture_index = 9
            self.last_texture_index = 9
            self.default_texture = self.texture_index
            self.demo_song = None
            self.navigator.reset_items()
            self.navigator.get_current_item().box.get_scores()
            self.screen_init = True
            self.last_moved = get_current_ms()
            self.ura_toggle = 0
            self.ura_switch_animation = UraSwitchAnimation()
            self.is_ura = False
            if str(global_data.selected_song) in self.navigator.all_song_files:
                self.navigator.mark_crowns_dirty_for_song(self.navigator.all_song_files[str(global_data.selected_song)])

    def on_screen_end(self, next_screen):
        self.screen_init = False
        global_data.selected_song = self.navigator.get_current_item().path
        session_data.selected_difficulty = self.selected_difficulty
        self.reset_demo_music()
        self.navigator.reset_items()
        audio.unload_all_sounds()
        tex.unload_textures()
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
            self.wait = get_current_ms()
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
            else:
                selected_song = self.navigator.select_current_item()
                if selected_song:
                    self.state = State.SONG_SELECTED
                    if 4 not in selected_song.tja.metadata.course_data:
                        self.is_ura = False
                    audio.play_sound(self.sound_don)
                    self.move_away.start()
                    self.diff_fade_out.start()
                    self.text_fade_out.start()
                    self.text_fade_in.start()

    def handle_input_selected(self):
        # Handle song selection confirmation or cancel
        if is_l_don_pressed() or is_r_don_pressed():
            if self.selected_difficulty == -1:
                self._cancel_selection()
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
        if self.is_ura and self.selected_difficulty == 4:
            self.selected_difficulty = 2
        elif self.selected_difficulty == -1:
            pass
        elif self.selected_difficulty not in diffs:
            self.selected_difficulty = min(diffs)
        elif self.selected_difficulty == min(diffs):
            self.selected_difficulty = -1
        else:
            self.selected_difficulty = diffs[diffs.index(self.selected_difficulty) - 1]

    def _navigate_difficulty_right(self, diffs):
        """Navigate difficulty selection rightward"""
        if self.is_ura and self.selected_difficulty == 2:
            self.selected_difficulty = 4

        if (self.selected_difficulty in [3, 4] and 4 in diffs):
            self.ura_toggle = (self.ura_toggle + 1) % 10
            if self.ura_toggle == 0:
                self._toggle_ura_mode()
        elif self.selected_difficulty not in diffs:
            self.selected_difficulty = min(diffs)
        elif self.selected_difficulty < max(diffs):
            self.selected_difficulty = diffs[diffs.index(self.selected_difficulty) + 1]

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

    def update(self):
        self.on_screen_start()
        self.background_move.update(get_current_ms())
        self.move_away.update(get_current_ms())
        self.diff_fade_out.update(get_current_ms())
        self.background_fade_change.update(get_current_ms())
        self.text_fade_out.update(get_current_ms())
        self.text_fade_in.update(get_current_ms())
        self.ura_switch_animation.update(get_current_ms())

        if self.text_fade_out.is_finished:
            self.selected_song = True

        if self.background_move.is_finished:
            self.background_move.restart()

        if self.last_texture_index != self.texture_index:
            if not self.background_fade_change.is_started:
                self.background_fade_change.start()
            if self.background_fade_change.is_finished:
                self.last_texture_index = self.texture_index

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

        for song in self.navigator.items:
            song.box.update(self.state == State.SONG_SELECTED)
            song.box.is_open = song.box.position == SongSelectScreen.BOX_CENTER + 150
            if not isinstance(song, Directory) and song.box.is_open:
                if self.demo_song is None and get_current_ms() >= song.box.wait + (83.33*3):
                    song.box.get_scores()
                    if song.tja.metadata.wave.exists() and song.tja.metadata.wave.is_file():
                        self.demo_song = audio.load_music_stream(song.tja.metadata.wave, preview=song.tja.metadata.demostart, normalize=0.1935)
                        audio.play_music_stream(self.demo_song)
                        audio.stop_sound(self.sound_bgm)
            if song.box.is_open:
                current_box = song.box
                if not current_box.is_back and get_current_ms() >= song.box.wait + (83.33*3):
                    self.texture_index = current_box.texture_index

        if ray.is_key_pressed(ray.KeyboardKey.KEY_ESCAPE):
            return self.on_screen_end('ENTRY')

    def draw_selector(self):
        if self.selected_difficulty == -1:
            tex.draw_texture('diff_select', '1p_outline_back')
        else:
            difficulty = min(3, self.selected_difficulty)
            tex.draw_texture('diff_select', '1p_balloon', x=(difficulty * 115))
            tex.draw_texture('diff_select', '1p_outline', x=(difficulty * 115))

    def draw(self):
        # Draw file/directory list
        width = tex.textures['box']['background'].width
        for i in range(0, width * 4, width):
            tex.draw_texture('box', 'background', frame=self.last_texture_index, x=i - int(self.background_move.attribute))
            reverse_color = ray.fade(ray.WHITE, 1 - self.background_fade_change.attribute)
            tex.draw_texture('box', 'background', frame=self.texture_index, x=i - int(self.background_move.attribute), color=reverse_color)

        if self.navigator.genre_bg is not None and self.state == State.BROWSING:
            self.navigator.genre_bg.draw(95)
        for item in self.navigator.items:
            box = item.box
            if -156 <= box.position <= self.screen_width + 144:
                if box.position <= 500:
                    box.draw(box.position - int(self.move_away.attribute), 95, self.is_ura, fade_override=self.diff_fade_out.attribute)
                else:
                    box.draw(box.position + int(self.move_away.attribute), 95, self.is_ura, fade_override=self.diff_fade_out.attribute)

        self.ura_switch_animation.draw()

        if self.selected_song and self.state == State.SONG_SELECTED:
            self.draw_selector()
            fade = ray.fade(ray.WHITE, self.text_fade_in.attribute)
            tex.draw_texture('global', 'difficulty_select', color=fade)
        else:
            fade = ray.fade(ray.WHITE, self.text_fade_out.attribute)
            tex.draw_texture('global', 'song_select', color=fade)

        tex.draw_texture('global', 'footer')

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
        8: ray.Color(148, 24, 0, 255)
    }
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
        self.is_back = self.texture_index == 17
        self.name = None
        self.black_name = None
        self.hori_name = None
        self.yellow_box = None
        self.open_anim = Animation.create_move(133, start_position=0, total_distance=150, delay=83.33)
        self.open_fade = Animation.create_fade(200, initial_opacity=0, final_opacity=1.0)
        self.move = None
        self.wait = 0
        self.is_dir = is_dir
        self.is_genre_start = 0
        self.is_genre_end = False
        self.genre_distance = 0
        self.tja_count = tja_count
        self.tja_count_text = None
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
        if self.yellow_box is not None:
            self.yellow_box.update(is_diff_select)

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
        if self.tja_count is not None and self.tja_count > 0 and self.tja_count_text is None:
            self.tja_count_text = OutlinedText(str(self.tja_count), 35, ray.WHITE, ray.BLACK, outline_thickness=5)#, horizontal_spacing=1.2)
        if self.box_texture is None and self.box_texture_path is not None:
            self.box_texture = ray.load_texture(self.box_texture_path)

        self.open_anim.update(get_current_ms())
        self.open_fade.update(get_current_ms())

        if self.name is None and -56 <= self.position <= 1280:
            self.name = OutlinedText(self.text_name, 40, ray.WHITE, SongBox.OUTLINE_MAP.get(self.name_texture_index, ray.Color(101, 0, 82, 255)), outline_thickness=5, vertical=True)


    def _draw_closed(self, x: int, y: int):
        tex.draw_texture('box', 'folder_texture_left', frame=self.texture_index, x=x)
        offset = 1 if self.texture_index in {3, 9, 17} else 0
        tex.draw_texture('box', 'folder_texture', frame=self.texture_index, x=x, x2=32, y=offset)
        tex.draw_texture('box', 'folder_texture_right', frame=self.texture_index, x=x)
        if self.texture_index == 9:
            tex.draw_texture('box', 'genre_overlay', x=x, y=y)
        if not self.is_back and self.is_dir:
            tex.draw_texture('box', 'folder_clip', frame=self.texture_index, x=x - (1 - offset), y=y)

        if self.is_back:
            tex.draw_texture('box', 'back_text', x=x, y=y)
        elif self.name is not None:
            dest = ray.Rectangle(x + 47 - int(self.name.texture.width / 2), y+35, self.name.texture.width, min(self.name.texture.height, 417))
            self.name.draw(self.name.default_src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        if self.tja is not None and self.tja.ex_data.new:
            tex.draw_texture('yellow_box', 'ex_data_new_song_balloon', x=x, y=y)
        if self.scores:
            highest_key = max(self.scores.keys())
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
        offset = 1 if self.texture_index in {3, 9, 17} else 0
        tex.draw_texture('box', 'folder_texture', frame=self.texture_index, x=x - self.open_anim.attribute, y=offset, x2=324)
        tex.draw_texture('box', 'folder_texture_right', frame=self.texture_index, x=x + self.open_anim.attribute)

        if self.texture_index == 9:
            tex.draw_texture('box', 'genre_overlay_large', x=x, y=y, color=color)
        color = ray.WHITE
        if fade_override is not None:
            color = ray.fade(ray.WHITE, min(0.5, fade_override))
        tex.draw_texture('yellow_box', 'song_count_back', color=color)

        color = ray.WHITE
        if fade_override is not None:
            color = ray.fade(ray.WHITE, fade_override)
        if self.tja_count_text is not None:
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
            self.subtitle = OutlinedText(self.tja.metadata.subtitle.get(global_data.config['general']['language'], ''), 30, ray.WHITE, ray.BLACK, outline_thickness=5, vertical=True)

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
        self.bottom_y = tex.textures['yellow_box']['yellow_box_bottom_right'].y
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
            tex.draw_texture('yellow_box', 's_crown_outline', x=(diff*60), color=ray.fade(ray.WHITE, min(fade, 0.25)))

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
                tex.draw_texture('yellow_box', 'difficulty_bar_shadow', frame=i, x=(i*60), color=ray.fade(ray.WHITE, min(fade, 0.25)))

        for diff in self.tja.metadata.course_data:
            if diff >= 4:
                continue
            for j in range(self.tja.metadata.course_data[diff].level):
                tex.draw_texture('yellow_box', 'star', x=(diff*60), y=(j*-17), color=color)

    def _draw_tja_data_diff(self, is_ura: bool):
        if self.tja is None:
            return
        color = ray.fade(ray.WHITE, self.fade_in.attribute)
        tex.draw_texture('diff_select', 'back', color=color)

        for i in range(4):
            if i == 3 and is_ura:
                tex.draw_texture('diff_select', 'diff_tower', frame=4, x=(i*115), color=color)
                tex.draw_texture('diff_select', 'ura_oni_plate', color=color)
            else:
                tex.draw_texture('diff_select', 'diff_tower', frame=i, x=(i*115), color=color)
            if i not in self.tja.metadata.course_data:
                tex.draw_texture('diff_select', 'diff_tower_shadow', frame=i, x=(i*115), color=ray.fade(ray.WHITE, min(self.fade_in.attribute, 0.25)))

        for course in self.tja.metadata.course_data:
            if (course == 4 and not is_ura) or (course == 3 and is_ura):
                continue
            for j in range(self.tja.metadata.course_data[course].level):
                tex.draw_texture('yellow_box', 'star_ura', x=min(course, 3)*115, y=(j*-20), color=color)

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
            dest = ray.Rectangle(x - 22, y, texture.width, min(texture.height, 410))
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
            color = ray.fade(ray.WHITE, fade)
            if self.is_back:
                tex.draw_texture('box', 'back_graphic', color=color)
            self._draw_tja_data(song_box, color, fade)

        self._draw_text(song_box)

class GenreBG:
    def __init__(self, start_box: SongBox, end_box: SongBox, title: OutlinedText):
        self.start_box = start_box
        self.end_box = end_box
        self.start_position = start_box.position
        self.end_position = end_box.position
        self.title = title
        self.fade_in = Animation.create_fade(116, initial_opacity=0.0, final_opacity=1.0, ease_in='quadratic', delay=50)
        self.fade_in.start()
    def update(self, current_ms):
        self.start_position = self.start_box.position
        self.end_position = self.end_box.position
        self.fade_in.update(current_ms)
    def draw(self, y):
        color = ray.fade(ray.WHITE, self.fade_in.attribute)
        offset = -150 if self.start_box.is_open else 0

        tex.draw_texture('box', 'folder_background_edge', frame=self.end_box.texture_index, x=self.start_position+offset, y=y, mirror="horizontal", color=color)
        extra_distance = 155 if self.end_box.is_open or self.start_box.is_open else 0
        if self.start_position >= -56 and self.end_position < self.start_position:
            x2 = self.start_position + 1336
        else:
            x2 = abs(self.end_position) - self.start_position + extra_distance + 57
        tex.draw_texture('box', 'folder_background', x=self.start_position+offset, y=y, x2=x2, frame=self.end_box.texture_index)
        if self.end_position < self.start_position and self.end_position >= -56:
            x2 = min(self.end_position+75, 1280) + extra_distance
            tex.draw_texture('box', 'folder_background', x=-18, y=y, x2=x2, frame=self.end_box.texture_index)
        offset = 150 if self.end_box.is_open else 0
        tex.draw_texture('box', 'folder_background_edge', x=self.end_position+80+offset, y=y, color=color, frame=self.end_box.texture_index)

        if ((self.start_position <= 594 and self.end_position >= 594) or
            ((self.start_position <= 594 or self.end_position >= 594) and (self.start_position > self.end_position))):
            dest_width = min(300, self.title.texture.width)
            tex.draw_texture('box', 'folder_header', x=-(dest_width//2), y=y, x2=dest_width, color=color, frame=self.end_box.texture_index)
            tex.draw_texture('box', 'folder_header_edge', x=-(dest_width//2), y=y, color=color, frame=self.end_box.texture_index, mirror="horizontal")
            tex.draw_texture('box', 'folder_header_edge', x=(dest_width//2), y=y, color=color, frame=self.end_box.texture_index)
            dest = ray.Rectangle((1280//2) - (dest_width//2), y-60, dest_width, self.title.texture.height)
            self.title.draw(self.title.default_src, dest, ray.Vector2(0, 0), 0, color)

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
        tex.draw_texture('diff_select', 'ura_switch', frame=self.texture_change.attribute, color=ray.fade(ray.WHITE, self.fade_out.attribute))

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
    }
    """Base class for files and directories in the navigation system"""
    def __init__(self, path: Path, name: str):
        self.path = path
        self.selected = False

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

        if self.to_root or self.back:
            texture_index = 17

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
        self.root_items: list[Union[Directory, SongFile]] = []

        # OPTION 2: Lazy crown calculation with caching
        self.directory_crowns: dict[str, dict] = dict()  # path -> crown list
        self.crown_cache_dirty: set[str] = set()  # directories that need crown recalculation

        # Navigation state
        self.in_root_selection = True
        self.current_dir = Path()
        self.current_root_dir = Path()
        self.items: list[Directory | SongFile] = []
        self.new_items: list[Directory | SongFile] = []
        self.selected_index = 0
        self.history = []
        self.box_open = False
        self.genre_bg = None
        self.song_count = 0

        # Generate all objects upfront
        self._generate_all_objects()
        self.load_root_directories()

    def _generate_all_objects(self):
        """Generate all Directory and SongFile objects in advance"""
        print("Generating all Directory and SongFile objects...")

        # First, generate objects for each root directory
        for root_path in self.root_dirs:
            if not root_path.exists():
                print(f"Root directory does not exist: {root_path}")
                continue

            self._generate_objects_recursive(root_path, is_root=True)

        print(f"Object generation complete. "
                    f"Directories: {len(self.all_directories)}, "
                    f"Songs: {len(self.all_song_files)}")

    def _generate_objects_recursive(self, dir_path: Path, is_root=False):
            """Recursively generate Directory and SongFile objects for a directory"""
            if not dir_path.is_dir():
                return

            dir_key = str(dir_path)

            # Check for box.def
            has_box_def = (dir_path / "box.def").exists()

            # Parse box.def if it exists
            name = dir_path.name if dir_path.name else str(dir_path)
            texture_index = 620
            box_texture = None
            collection = None

            if has_box_def:
                name, texture_index, collection = self._parse_box_def(dir_path)
                box_png_path = dir_path / "box.png"
                if box_png_path.exists():
                    box_texture = str(box_png_path)

            # Count TJA files for this directory
            tja_count = self._count_tja_files(dir_path)

            # Create Directory object
            directory_obj = Directory(
                dir_path, name, texture_index,
                has_box_def=has_box_def,
                tja_count=tja_count,
                box_texture=box_texture,
                collection=collection
            )
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
            for i, tja_path in enumerate(sorted(tja_files)):
                song_key = str(tja_path)
                if song_key not in self.all_song_files:
                    song_obj = SongFile(tja_path, tja_path.name, texture_index)
                    self.song_count += 1
                    global_data.song_progress = self.song_count / global_data.total_songs
                    if song_obj.is_recent:
                        self.new_items.append(SongFile(tja_path, tja_path.name, 620, name_texture_index=texture_index))
                    self.all_song_files[song_key] = song_obj

                content_items.append(self.all_song_files[song_key])

            # Store content for this directory
            self.directory_contents[dir_key] = content_items

            # OPTION 2: Mark directory for lazy crown calculation
            self.crown_cache_dirty.add(dir_key)

            # If this is a root directory, add to root items
            if is_root:
                if has_box_def:
                    self.root_items.append(directory_obj)
                else:
                    # For roots without box.def, add their TJA files directly
                    all_tja_files = self._find_tja_files_recursive(dir_path)
                    for tja_path in sorted(all_tja_files):
                        song_key = str(tja_path)
                        if song_key not in self.all_song_files:
                            try:
                                song_obj = SongFile(tja_path, tja_path.name, 9)
                                self.song_count += 1
                                global_data.song_progress = self.song_count / global_data.total_songs
                                self.all_song_files[song_key] = song_obj
                            except Exception as e:
                                print(f"Error creating SongFile for {tja_path}: {e}")
                                continue
                        self.root_items.append(self.all_song_files[song_key])

    def _count_tja_files(self, folder_path: Path):
        """Count TJA files in directory (matching original logic)"""
        tja_count = 0

        # Find all song_list.txt files recursively
        song_list_files = list(folder_path.rglob("song_list.txt"))

        if song_list_files:
            # Process all song_list.txt files found
            for song_list_path in song_list_files:
                try:
                    with open(song_list_path, 'r', encoding='utf-8-sig') as song_list_file:
                        tja_count += len([line for line in song_list_file.readlines() if line.strip()])
                except (IOError, UnicodeDecodeError) as e:
                    # Handle potential file reading errors
                    print(f"Warning: Could not read {song_list_path}: {e}")
                    continue
        else:
            # Fallback: Use recursive counting of .tja files
            tja_count = sum(1 for _ in folder_path.rglob("*.tja"))

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

        for tja_path in sorted(tja_files):
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
            # For directories with box.def, we want their direct TJA files
            # Set box_def_dirs_only=False to ensure we get files from this directory
            return self._find_tja_files_in_directory_only(directory)

    def _find_tja_files_in_directory_only(self, directory: Path):
        """Find TJA files only in the specified directory, not recursively in subdirectories with box.def"""
        tja_files: list[Path] = []

        try:
            for path in directory.iterdir():
                if path.is_file() and path.suffix.lower() == ".tja":
                    tja_files.append(path)
                elif path.is_dir():
                    # Only recurse into subdirectories that don't have box.def
                    sub_dir_has_box_def = (path / "box.def").exists()
                    if not sub_dir_has_box_def:
                        tja_files.extend(self._find_tja_files_in_directory_only(path))
        except (PermissionError, OSError):
            pass

        return tja_files

    def _find_tja_files_recursive(self, directory: Path, box_def_dirs_only=True):
        tja_files: list[Path] = []

        try:
            has_box_def = (directory / "box.def").exists()
            # Fixed: Only skip if box_def_dirs_only is True AND has_box_def AND it's not the directory we're currently processing
            # During object generation, we want to get files from directories with box.def
            if box_def_dirs_only and has_box_def and directory != self.current_dir:
                # This logic should only apply during navigation, not during object generation
                # During object generation, we want to collect all TJA files
                return []

            for path in directory.iterdir():
                if path.is_file() and path.suffix.lower() == ".tja":
                    tja_files.append(path)
                elif path.is_dir():
                    sub_dir_has_box_def = (path / "box.def").exists()
                    if not sub_dir_has_box_def:
                        tja_files.extend(self._find_tja_files_recursive(path, box_def_dirs_only))
        except (PermissionError, OSError):
            pass

        return tja_files

    def _parse_box_def(self, path: Path):
        """Parse box.def file for directory metadata"""
        texture_index = 9
        name = path.name
        collection = None

        try:
            with open(path / "box.def", 'r', encoding='utf-8') as box_def:
                for line in box_def:
                    line = line.strip()
                    if line.startswith("#GENRE:"):
                        genre = line.split(":", 1)[1].strip()
                        texture_index = FileSystemItem.GENRE_MAP.get(genre, 620)
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
                    if file_path.exists():
                        tja_files.append(file_path)
                else:
                    # Try to find by title and subtitle
                    for key, value in global_data.song_hashes.items():
                        for i in range(len(value)):
                            song = value[i]
                            if (song["title"]["en"] == title and
                                song["subtitle"]["en"][2:] == subtitle and
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

    def set_base_positions(self):
        """Set initial positions for all items"""
        self.calculate_box_positions()

    def load_root_directories(self):
        """Load the pre-generated root directory items"""
        self.items = self.root_items.copy()
        self.in_root_selection = True
        self.current_dir = Path()
        self.current_root_dir = Path()

        # Reset selection
        self.selected_index = 0 if self.items else -1
        self.calculate_box_positions()

    def load_current_directory(self, selected_item: Optional[Directory]=None):
        """Load pre-generated items for the current directory"""
        has_children = any(item.is_dir() and (item / "box.def").exists() for item in self.current_dir.iterdir())
        self.genre_bg = None
        if has_children:
            self.items = []
            if not self.box_open:
                self.selected_index = 0

        dir_key = str(self.current_dir)
        start_box = None
        end_box = None

        # Add back/to_root navigation items
        if self.current_dir != self.current_root_dir:
            back_dir = Directory(self.current_dir.parent, "", 17, back=True)
            if not has_children:
                start_box = back_dir.box
            self.items.insert(self.selected_index, back_dir)
        elif not self.in_root_selection:
            to_root_dir = Directory(Path(), "", 17, to_root=True)
            self.items.append(to_root_dir)

        # Add pre-generated content for this directory
        if dir_key in self.directory_contents:
            content_items = self.directory_contents[dir_key]
            if isinstance(selected_item, Directory) and selected_item.collection == Directory.COLLECTIONS[0]:
                content_items = self.new_items

            i = 1
            for item in content_items:
                if isinstance(item, SongFile):
                    if i % 10 == 0 and i != 0:
                        back_dir = Directory(self.current_dir.parent, "", 17, back=True)
                        self.items.insert(self.selected_index+i, back_dir)
                        i += 1

                if not has_children:
                    self.items.insert(self.selected_index+i, item)
                else:
                    self.items.append(item)
                i += 1

            if not has_children:
                self.box_open = True
                end_box = content_items[-1].box
                if selected_item in self.items:
                    self.items.remove(selected_item)
        # OPTIMIZED: Use cached crowns (calculated on-demand)
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
            self.genre_bg = GenreBG(start_box, end_box, selected_item.box.hori_name)

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

    def select_current_item(self):
        """Select the currently highlighted item"""
        if not self.items or self.selected_index >= len(self.items):
            return

        selected_item = self.items[self.selected_index]

        if isinstance(selected_item, Directory):
            if self.box_open:
                self.go_back()
            if selected_item.to_root:
                self.load_root_directories()
            else:
                # Save current state to history
                if self.current_dir is not None:
                    self.history.append((self.current_dir, self.selected_index, self.in_root_selection, self.current_root_dir))
                self.current_dir = selected_item.path
                if self.in_root_selection:
                    self.current_root_dir = selected_item.path
                    self.in_root_selection = False
                self.load_current_directory(selected_item=selected_item)

        elif isinstance(selected_item, SongFile):
            return selected_item

    def go_back(self):
        """Navigate back to the previous directory"""
        if self.history:
            previous_dir, previous_index, previous_in_root, previous_root_dir = self.history.pop()
            self.current_dir = previous_dir
            self.selected_index = previous_index
            self.in_root_selection = previous_in_root
            self.current_root_dir = previous_root_dir
            if self.in_root_selection:
                self.load_root_directories()
            else:
                self.load_current_directory()
                self.box_open = False

    def get_current_item(self):
        """Get the currently selected item"""
        if self.items and 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        raise Exception("No current item available")

    def reset_items(self):
        for item in self.items:
            item.box.reset()

    def regenerate_objects(self):
        """Regenerate all objects (useful if files have changed on disk)"""
        print("Regenerating all objects...")

        # Clear existing objects
        self.all_directories.clear()
        self.all_song_files.clear()
        self.directory_contents.clear()
        self.root_items.clear()
        self.directory_crowns.clear()  # Clear crown cache
        self.crown_cache_dirty.clear()  # Clear dirty flags

        # Regenerate everything
        self._generate_all_objects()

        # Reset navigation state
        self.current_dir = Path()
        self.current_root_dir = Path()
        self.history.clear()
        self.load_root_directories()
