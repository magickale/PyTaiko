
import sqlite3
from pathlib import Path
from typing import Optional, Union

import pyray as ray

from libs import song_hash
from libs.animation import Animation
from libs.audio import audio
from libs.tja import TJAParser
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
    load_all_textures_from_zip,
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

        self.navigator = FileNavigator(self.root_dir)

    def load_textures(self):
        self.textures = load_all_textures_from_zip(Path('Graphics/lumendata/song_select.zip'))
        self.textures['custom'] = [ray.load_texture('1.png'), ray.load_texture('2.png')]

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(sounds_dir / "inst_00_don.wav")
        self.sound_kat = audio.load_sound(sounds_dir / "inst_00_katsu.wav")
        self.sound_skip = audio.load_sound(sounds_dir / 'song_select' / 'Skip.ogg')
        self.sound_ura_switch = audio.load_sound(sounds_dir / 'song_select' / 'SE_SELECT [4].ogg')
        audio.set_sound_volume(self.sound_ura_switch, 0.25)
        self.sound_bgm = audio.load_sound(sounds_dir / "song_select" / "JINGLE_GENRE [1].ogg")
        #self.sound_cancel = audio.load_sound(sounds_dir / "cancel.wav")

    def on_screen_start(self):
        if not self.screen_init:
            self.load_textures()
            self.load_sounds()
            self.selected_song = None
            self.selected_difficulty = -1
            self.game_transition = None
            self.move_away = Animation.create_move(float('inf'))
            self.diff_fade_out = Animation.create_fade(0, final_opacity=1.0)
            self.background_move = Animation.create_move(15000, start_position=0, total_distance=1280)
            self.state = State.BROWSING
            self.text_fade_out = None
            self.text_fade_in = None
            self.texture_index = 784
            self.last_texture_index = 784
            self.background_fade_change = None
            self.demo_song = None
            for item in self.navigator.items:
                item.box.reset()
            self.navigator.get_current_item().box.get_scores()
            self.screen_init = True
            self.last_moved = get_current_ms()
            self.ura_toggle = 0
            self.ura_switch_animation = None
            self.is_ura = False
            if str(global_data.selected_song) in self.navigator.all_song_files:
                self.navigator.mark_crowns_dirty_for_song(self.navigator.all_song_files[str(global_data.selected_song)])

    def on_screen_end(self, next_screen):
        self.screen_init = False
        global_data.selected_song = self.navigator.get_current_item().path
        session_data.selected_difficulty = self.selected_difficulty
        audio.unload_sound(self.sound_bgm)
        self.reset_demo_music()
        for zip in self.textures:
            for texture in self.textures[zip]:
                ray.unload_texture(texture)
        return next_screen

    def reset_demo_music(self):
        if self.demo_song is not None:
            audio.stop_music_stream(self.demo_song)
            audio.unload_music_stream(self.demo_song)
            audio.play_sound(self.sound_bgm)
        self.demo_song = None
        self.navigator.get_current_item().box.wait = get_current_ms()

    def handle_input(self):
        if self.state == State.BROWSING:
            if ray.is_key_pressed(ray.KeyboardKey.KEY_LEFT_CONTROL) or (is_l_kat_pressed() and get_current_ms() <= self.last_moved + 100):
                self.reset_demo_music()
                self.wait = get_current_ms()
                for i in range(10):
                    self.navigator.navigate_left()
                audio.play_sound(self.sound_skip)
                self.last_moved = get_current_ms()
            elif ray.is_key_pressed(ray.KeyboardKey.KEY_RIGHT_CONTROL) or (is_r_kat_pressed() and get_current_ms() <= self.last_moved + 100):
                self.reset_demo_music()
                for i in range(10):
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
                if selected_item is not None and selected_item.box.texture_index == 552:
                    self.navigator.go_back()
                    #audio.play_sound(self.sound_cancel)
                else:
                    selected_song = self.navigator.select_current_item()
                    if selected_song:
                        self.state = State.SONG_SELECTED
                        if 4 not in selected_song.tja.metadata.course_data:
                            self.is_ura = False
                        audio.play_sound(self.sound_don)
                        self.move_away = Animation.create_move(233, total_distance=500)
                        self.diff_fade_out = Animation.create_fade(83)

        elif self.state == State.SONG_SELECTED:
            # Handle song selection confirmation or cancel
            if is_l_don_pressed() or is_r_don_pressed():
                if self.selected_difficulty == -1:
                    self.selected_song = None
                    self.move_away = Animation.create_move(float('inf'))
                    self.diff_fade_out = Animation.create_fade(0, final_opacity=1.0)
                    self.text_fade_out = None
                    self.text_fade_in = None
                    self.state = State.BROWSING
                    for item in self.navigator.items:
                        item.box.reset()
                else:
                    audio.play_sound(self.sound_don)
                    self.game_transition = Transition(self.screen_height)
            if is_l_kat_pressed():
                audio.play_sound(self.sound_kat)
                selected_song = self.navigator.get_current_item()
                if not isinstance(selected_song, Directory):
                    diffs = sorted([item for item in selected_song.tja.metadata.course_data])
                    if self.is_ura and self.selected_difficulty == 4:
                        self.selected_difficulty = 2
                    elif self.selected_difficulty == -1:
                        pass
                    elif self.selected_difficulty not in diffs:
                        self.selected_difficulty = min(diffs)
                    elif self.selected_difficulty == min(diffs):
                        self.selected_difficulty = -1
                    elif self.selected_difficulty > min(diffs):
                        self.selected_difficulty = (diffs[diffs.index(self.selected_difficulty) - 1])
                else:
                    raise Exception("Directory was chosen instead of song")
            if is_r_kat_pressed():
                audio.play_sound(self.sound_kat)
                selected_song = self.navigator.get_current_item()
                if not isinstance(selected_song, Directory):
                    diffs = sorted([item for item in selected_song.tja.metadata.course_data])
                    if self.is_ura and self.selected_difficulty == 2:
                        self.selected_difficulty = 4
                    if (self.selected_difficulty == 3 or self.selected_difficulty == 4) and 4 in diffs:
                        self.ura_toggle = (self.ura_toggle + 1) % 10
                        if self.ura_toggle == 0:
                            self.is_ura = not self.is_ura
                            self.ura_switch_animation = UraSwitchAnimation(not self.is_ura)
                            audio.play_sound(self.sound_ura_switch)
                            self.selected_difficulty = 7 - self.selected_difficulty
                    elif self.selected_difficulty not in diffs:
                        self.selected_difficulty = min(diffs)
                    elif self.selected_difficulty < max(diffs):
                        self.selected_difficulty = (diffs[diffs.index(self.selected_difficulty) + 1])
                else:
                    raise Exception("Directory was chosen instead of song")
            if ray.is_key_pressed(ray.KeyboardKey.KEY_TAB) and (self.selected_difficulty == 3 or self.selected_difficulty == 4):
                self.ura_toggle = 0
                self.is_ura = not self.is_ura
                self.ura_switch_animation = UraSwitchAnimation(not self.is_ura)
                audio.play_sound(self.sound_ura_switch)
                self.selected_difficulty = 7 - self.selected_difficulty

    def update(self):
        self.on_screen_start()
        if self.background_move.is_finished:
            self.background_move = Animation.create_move(15000, start_position=0, total_distance=1280)
        self.background_move.update(get_current_ms())

        if self.game_transition is not None:
            self.game_transition.update(get_current_ms())
            if self.game_transition.is_finished:
                return self.on_screen_end("GAME")
        else:
            self.handle_input()

        if self.demo_song is not None:
            audio.update_music_stream(self.demo_song)

        if self.background_fade_change is None:
            self.last_texture_index = self.texture_index
        for song in self.navigator.items:
            song.box.update(self.state == State.SONG_SELECTED)
            song.box.is_open = song.box.position == SongSelectScreen.BOX_CENTER + 150
            if not isinstance(song, Directory) and song.box.is_open:
                if self.demo_song is None and get_current_ms() >= song.box.wait + (83.33*3):
                    song.box.get_scores()
                    self.demo_song = audio.load_music_stream(song.tja.metadata.wave, preview=song.tja.metadata.demostart, normalize=0.1935)
                    audio.play_music_stream(self.demo_song)
                    audio.stop_sound(self.sound_bgm)
            if song.box.is_open:
                current_box = song.box
                if current_box.texture_index != 552 and get_current_ms() >= song.box.wait + (83.33*3):
                    self.texture_index = SongBox.BACKGROUND_MAP[current_box.texture_index]

        if self.last_texture_index != self.texture_index and self.background_fade_change is None:
            self.background_fade_change = Animation.create_fade(200)

        self.move_away.update(get_current_ms())
        self.diff_fade_out.update(get_current_ms())

        if self.background_fade_change is not None:
            self.background_fade_change.update(get_current_ms())
            if self.background_fade_change.is_finished:
                self.background_fade_change = None

        if self.move_away.is_finished and self.text_fade_out is None:
            self.text_fade_out = Animation.create_fade(33)
            self.text_fade_in = Animation.create_fade(33, initial_opacity=0.0, final_opacity=1.0, delay=self.text_fade_out.duration)

        if self.text_fade_out is not None:
            self.text_fade_out.update(get_current_ms())
            if self.text_fade_out.is_finished:
                self.selected_song = True

        if self.text_fade_in is not None:
            self.text_fade_in.update(get_current_ms())

        if self.ura_switch_animation is not None:
            self.ura_switch_animation.update(get_current_ms())

        if self.navigator.genre_bg is not None:
            self.navigator.genre_bg.update()

        if ray.is_key_pressed(ray.KeyboardKey.KEY_ESCAPE):
            return self.on_screen_end('ENTRY')

    def draw_selector(self):
        if self.selected_difficulty == -1:
            ray.draw_texture(self.textures['song_select'][133], 314, 110, ray.WHITE)
        else:
            difficulty = min(3, self.selected_difficulty)
            ray.draw_texture(self.textures['song_select'][140], 450 + (difficulty * 115), 7, ray.WHITE)
            ray.draw_texture(self.textures['song_select'][131], 461 + (difficulty * 115), 132, ray.WHITE)

    def draw(self):
        # Draw file/directory list
        texture_back = self.textures['song_select'][self.last_texture_index]
        texture = self.textures['song_select'][self.texture_index]
        for i in range(0, texture.width * 4, texture.width):
            if self.background_fade_change is not None:
                color = ray.fade(ray.WHITE, self.background_fade_change.attribute)
                ray.draw_texture(texture_back, i - int(self.background_move.attribute), 0, color)
                reverse_color = ray.fade(ray.WHITE, 1 - self.background_fade_change.attribute)
                ray.draw_texture(texture, i - int(self.background_move.attribute), 0, reverse_color)
            else:
                ray.draw_texture(texture, i - int(self.background_move.attribute), 0, ray.WHITE)

        if self.navigator.genre_bg is not None and self.state == State.BROWSING:
            self.navigator.genre_bg.draw(self.textures, 95)
        for item in self.navigator.items:
            box = item.box
            if -156 <= box.position <= self.screen_width + 144:
                if box.position <= 500:
                    box.draw(box.position - int(self.move_away.attribute), 95, self.textures, self.is_ura, fade_override=self.diff_fade_out.attribute)
                else:
                    box.draw(box.position + int(self.move_away.attribute), 95, self.textures, self.is_ura, fade_override=self.diff_fade_out.attribute)

        if self.ura_switch_animation is not None:
            self.ura_switch_animation.draw(self.textures)

        if self.selected_song and self.state == State.SONG_SELECTED:
            self.draw_selector()
            fade = ray.WHITE
            if self.text_fade_in is not None:
                fade = ray.fade(ray.WHITE, self.text_fade_in.attribute)
            ray.draw_texture(self.textures['song_select'][192], 5, 5, fade)
        else:
            fade = ray.WHITE
            if self.text_fade_out is not None:
                fade = ray.fade(ray.WHITE, self.text_fade_out.attribute)
            ray.draw_texture(self.textures['song_select'][244], 5, 5, fade)

        ray.draw_texture(self.textures['song_select'][394], 0, self.screen_height - self.textures['song_select'][394].height, ray.WHITE)

        if self.game_transition is not None:
            self.game_transition.draw(self.screen_height)

class SongBox:
    OUTLINE_MAP = {
        555: ray.Color(0, 77, 104, 255),
        560: ray.Color(156, 64, 2, 255),
        565: ray.Color(153, 4, 46, 255),
        570: ray.Color(60, 104, 0, 255),
        575: ray.Color(134, 88, 0, 255),
        580: ray.Color(79, 40, 134, 255),
        585: ray.Color(148, 24, 0, 255),
        615: ray.Color(84, 101, 126, 255)
    }
    FOLDER_HEADER_MAP = {
        555: 643,
        560: 645,
        565: 647,
        570: 649,
        575: 651,
        580: 653,
        585: 655,
        615: 667,
        620: 670
    }
    FULL_FOLDER_HEADER_MAP = {
        555: 736,
        560: 738,
        565: 740,
        570: 742,
        575: 744,
        580: 746,
        585: 748,
        615: 760,
        620: 762,
    }
    BACKGROUND_MAP = {
        555: 772,
        560: 773,
        565: 774,
        570: 775,
        575: 776,
        580: 777,
        585: 778,
        615: 783,
        620: 784
    }
    GENRE_CHAR_MAP = {
        555: 507,
        560: 509,
        565: 511,
        570: 513,
        575: 515,
        580: 517,
        585: 519,
        615: 532,
    }
    def __init__(self, name: str, texture_index: int, is_dir: bool, tja: Optional[TJAParser] = None,
        tja_count: Optional[int] = None, box_texture: Optional[ray.Texture] = None):
        self.text_name = name
        self.texture_index = texture_index
        self.box_texture = box_texture
        self.scores = dict()
        self.crown = dict()
        self.position = -11111
        self.start_position = -1
        self.target_position = -1
        self.is_open = False
        self.name = None
        self.subtitle = None
        self.black_name = None
        self.hori_name = None
        self.yellow_box = None
        self.open_anim = None
        self.open_fade = None
        self.move = None
        self.wait = 0
        self.is_dir = is_dir
        self.is_genre_start = 0
        self.is_genre_end = False
        self.genre_distance = 0
        self.tja_count = tja_count
        self.tja_count_text = None
        if self.tja_count is not None and self.tja_count != 0:
            self.tja_count_text = OutlinedText(str(self.tja_count), 35, ray.Color(255, 255, 255, 255), ray.Color(0, 0, 0, 255), outline_thickness=5, horizontal_spacing=1.2)
        self.tja = tja
        self.hash = dict()
        self.update(False)

    def reset(self):
        if self.black_name is not None:
            if self.tja is not None:
                subtitle = OutlinedText(self.tja.metadata.subtitle.get(global_data.config['general']['language'], ''), 30, ray.Color(255, 255, 255, 255), ray.Color(0, 0, 0, 255), outline_thickness=5, vertical=True)
            else:
                subtitle = None
            self.yellow_box = YellowBox(self.black_name, self.texture_index == 552, tja=self.tja, subtitle=subtitle)
        self.open_anim = None
        self.open_fade = None

    def get_scores(self):
        if self.tja is None:
            return

        with sqlite3.connect('scores.db') as con:
            cursor = con.cursor()

            diffs_to_compute = []
            for diff in self.tja.metadata.course_data:
                if diff not in self.hash:
                    diffs_to_compute.append(diff)

            if diffs_to_compute:
                for diff in diffs_to_compute:
                    notes, _, bars = TJAParser.notes_to_position(TJAParser(self.tja.file_path), diff)
                    self.hash[diff] = self.tja.hash_note_data(notes, bars)

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

    def update(self, is_diff_select):
        self.is_diff_select = is_diff_select
        if self.yellow_box is not None:
            self.yellow_box.update(is_diff_select)
        is_open_prev = self.is_open
        if self.position != self.target_position and self.move is None:
            if self.position < self.target_position:
                direction = 1
            else:
                direction = -1
            if abs(self.target_position - self.position) > 250:
                direction *= -1
            self.move = Animation.create_move(83.3, start_position=0, total_distance=100 * direction, ease_out='cubic')
            if self.is_open or self.target_position == SongSelectScreen.BOX_CENTER + 150:
                self.move.total_distance = 250 * direction
            self.start_position = self.position
        if self.move is not None:
            self.move.update(get_current_ms())
            self.position = self.start_position + int(self.move.attribute)
            if self.move.is_finished:
                self.position = self.target_position
                self.move = None
        self.is_open = self.position == SongSelectScreen.BOX_CENTER + 150
        if not is_open_prev and self.is_open:
            if self.black_name is None:
                self.black_name = OutlinedText(self.text_name, 40, ray.Color(255, 255, 255, 255), ray.Color(0, 0, 0, 255), outline_thickness=5, vertical=True)
                #print(f"loaded black name {self.text_name}")
            if self.tja is not None or self.texture_index == 552:
                if self.tja is not None:
                    subtitle = OutlinedText(self.tja.metadata.subtitle.get(global_data.config['general']['language'], ''), 30, ray.Color(255, 255, 255, 255), ray.Color(0, 0, 0, 255), outline_thickness=5, vertical=True)
                else:
                    subtitle = None
                self.yellow_box = YellowBox(self.black_name, self.texture_index == 552, tja=self.tja, subtitle=subtitle)
                self.yellow_box.create_anim()
            else:
                self.hori_name = OutlinedText(self.text_name, 40, ray.Color(255, 255, 255, 255), ray.Color(0, 0, 0, 255), outline_thickness=5)
                #print(f"loaded hori name {self.text_name}")
                self.open_anim = Animation.create_move(133, start_position=0, total_distance=150, delay=83.33)
                self.open_fade = Animation.create_fade(200, initial_opacity=0, final_opacity=1.0)
            self.wait = get_current_ms()

        elif not self.is_open:
            if self.black_name is not None:
                self.black_name.unload()
                self.black_name = None
            if self.yellow_box is not None:
                self.yellow_box = None
            if self.hori_name is not None:
                self.hori_name.unload()
                self.hori_name = None

        if self.open_anim is not None:
            self.open_anim.update(get_current_ms())
        if self.open_fade is not None:
            self.open_fade.update(get_current_ms())

        '''
        if self.black_name is None:
            self.black_name = OutlinedText(self.text_name, 40, ray.Color(255, 255, 255, 255), ray.Color(0, 0, 0, 255), outline_thickness=5, vertical=True)
        if self.name is None:
            self.name = OutlinedText(self.text_name, 40, ray.Color(255, 255, 255, 255), SongBox.OUTLINE_MAP.get(self.texture_index, ray.Color(101, 0, 82, 255)), outline_thickness=5, vertical=True)
        '''

        if self.name is None and -56 <= self.position <= 1280:
            self.name = OutlinedText(self.text_name, 40, ray.Color(255, 255, 255, 255), SongBox.OUTLINE_MAP.get(self.texture_index, ray.Color(101, 0, 82, 255)), outline_thickness=5, vertical=True)
            #print(f"loaded {self.text_name}")
        elif self.name is not None and (self.position < -56 or self.position > 1280):
            self.name.unload()
            self.name = None


    def _draw_closed(self, x: int, y: int, textures):
        ray.draw_texture(textures['song_select'][self.texture_index+1], x, y, ray.WHITE)
        offset = 0
        if 555 <= self.texture_index <= 600:
            offset = 1
        for i in range(0, textures['song_select'][self.texture_index].width * 4, textures['song_select'][self.texture_index].width):
            ray.draw_texture(textures['song_select'][self.texture_index], (x+32)+i, y - offset, ray.WHITE)
        ray.draw_texture(textures['song_select'][self.texture_index+2], x+64, y, ray.WHITE)
        if self.texture_index == 620:
            ray.draw_texture(textures['song_select'][self.texture_index+3], x+12, y+16, ray.WHITE)
        if self.texture_index != 552 and self.is_dir:
            ray.draw_texture(textures['song_select'][SongBox.FOLDER_HEADER_MAP[self.texture_index]], x+4 - offset, y-6, ray.WHITE)


        if self.texture_index == 552:
            ray.draw_texture(textures['song_select'][422], x + 47 - int(textures['song_select'][422].width / 2), y+35, ray.WHITE)
        elif self.name is not None:
            src = ray.Rectangle(0, 0, self.name.texture.width, self.name.texture.height)
            dest = ray.Rectangle(x + 47 - int(self.name.texture.width / 2), y+35, self.name.texture.width, min(self.name.texture.height, 417))
            self.name.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        if self.scores:
            highest_key = max(self.scores.keys())
            score = self.scores[highest_key]
            if score and score[3] == 0:
                ray.draw_texture(textures['song_select'][683+highest_key], x+20, y-30, ray.WHITE)
            elif score and score[4] == 1:
                ray.draw_texture(textures['song_select'][688+highest_key], x+20, y-30, ray.WHITE)
        if self.crown:
            highest_crown = max(self.crown)
            if self.crown[highest_crown] == 'FC':
                ray.draw_texture(textures['song_select'][683+highest_crown], x+20, y-30, ray.WHITE)
            else:
                ray.draw_texture(textures['song_select'][688+highest_crown], x+20, y-30, ray.WHITE)
        #ray.draw_text(str(self.position), x, y-25, 25, ray.GREEN)

    def _draw_open(self, x: int, y: int, textures, fade_override):
        if self.open_anim is not None:
            color = ray.WHITE
            if fade_override is not None:
                color = ray.fade(ray.WHITE, fade_override)
            if self.hori_name is not None and self.open_anim.attribute >= 100:
                texture = textures['song_select'][SongBox.FULL_FOLDER_HEADER_MAP[self.texture_index]]
                src = ray.Rectangle(0, 0, texture.width, texture.height)
                dest = ray.Rectangle(x-115+48, (y-56) + 150 - int(self.open_anim.attribute), texture.width+220, texture.height)
                ray.draw_texture_pro(texture, src, dest, ray.Vector2(0,0), 0, color)

                texture = textures['song_select'][SongBox.FULL_FOLDER_HEADER_MAP[self.texture_index]+1]
                src = ray.Rectangle(0, 0, -texture.width, texture.height)
                dest = ray.Rectangle(x-115, y-56 + 150 - int(self.open_anim.attribute), texture.width, texture.height)
                ray.draw_texture(texture, x+160, y-56 + 150 - int(self.open_anim.attribute), color)
                ray.draw_texture_pro(texture, src, dest, ray.Vector2(0,0), 0, color)

                src = ray.Rectangle(0, 0, self.hori_name.texture.width, self.hori_name.texture.height)
                dest_width = min(300, self.hori_name.texture.width)
                dest = ray.Rectangle((x + 48) - (dest_width//2), y-52 + 150 - int(self.open_anim.attribute), dest_width, self.hori_name.texture.height)
                self.hori_name.draw(src, dest, ray.Vector2(0, 0), 0, color)


            ray.draw_texture(textures['song_select'][self.texture_index+1], x - int(self.open_anim.attribute), y, ray.WHITE)

            offset = 0
            if 555 <= self.texture_index <= 600:
                offset = 1
            for i in range(0, textures['song_select'][self.texture_index].width * (5+int(self.open_anim.attribute / 4)), textures['song_select'][self.texture_index].width):
                ray.draw_texture(textures['song_select'][self.texture_index], ((x- int(self.open_anim.attribute))+32)+i, y - offset, ray.WHITE)

            ray.draw_texture(textures['song_select'][self.texture_index+2], x+64 + int(self.open_anim.attribute), y, ray.WHITE)

            color = ray.WHITE
            if self.texture_index == 620:
                ray.draw_texture(textures['song_select'][self.texture_index+4], x+12 - 150, y+16, color)
            if fade_override is not None:
                color = ray.fade(ray.WHITE, min(0.5, fade_override))
            ray.draw_texture(textures['song_select'][492], 470, 125, color)

            color = ray.WHITE
            if fade_override is not None:
                color = ray.fade(ray.WHITE, fade_override)
            if self.tja_count_text is not None:
                ray.draw_texture(textures['song_select'][493], 475, 125, color)
                ray.draw_texture(textures['song_select'][494], 600, 125, color)
                src = ray.Rectangle(0, 0, self.tja_count_text.texture.width, self.tja_count_text.texture.height)
                dest_width = min(124, self.tja_count_text.texture.width)
                dest = ray.Rectangle(560 - (dest_width//2), 118, dest_width, self.tja_count_text.texture.height)
                self.tja_count_text.draw(src, dest, ray.Vector2(0, 0), 0, color)
            if self.texture_index in SongBox.GENRE_CHAR_MAP:
                ray.draw_texture(textures['song_select'][SongBox.GENRE_CHAR_MAP[self.texture_index]+1], 650, 125, color)
                ray.draw_texture(textures['song_select'][SongBox.GENRE_CHAR_MAP[self.texture_index]], 470, 180, color)
            elif self.box_texture is not None:
                ray.draw_texture(self.box_texture, (x+48) - (self.box_texture.width//2), (y+130), color)

    def draw(self, x: int, y: int, textures, is_ura: bool, fade_override=None):
        if self.is_open and get_current_ms() >= self.wait + 83.33:
            if self.yellow_box is not None:
                self.yellow_box.draw(textures, self, fade_override, is_ura)
            else:
                if self.open_fade is not None:
                    self._draw_open(x, y, textures, self.open_fade.attribute)
        else:
            self._draw_closed(x, y, textures)

class GenreBG:
    BG_MAP = {
        555: 547,
        560: 558,
        565: 563,
        570: 568,
        575: 573,
        580: 578,
        585: 583,
        615: 613,
        620: 618
    }
    HEADER_MAP = {
        555: 423,
        560: 425,
        565: 427,
        570: 429,
        575: 431,
        580: 433,
        585: 435,
        615: 768,
        620: 447
    }
    def __init__(self, start_box: SongBox, end_box: SongBox, title: OutlinedText):
        self.start_box = start_box
        self.end_box = end_box
        self.start_position = start_box.position
        self.end_position = end_box.position
        self.title = title
    def update(self):
        self.start_position = self.start_box.position
        self.end_position = self.end_box.position
    def draw(self, textures, y):
        texture_index = GenreBG.BG_MAP[self.end_box.texture_index]

        offset = -150 if self.start_box.is_open else 0
        texture = textures['song_select'][texture_index]
        src = ray.Rectangle(0, 0, -texture.width, texture.height)
        dest = ray.Rectangle(self.start_position+offset-5, y-70, texture.width, texture.height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0,0), 0, ray.WHITE)

        extra_distance = 155 if self.end_box.is_open or self.start_box.is_open else 0
        x = self.start_position+18+offset
        texture = textures['song_select'][texture_index+1]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        if self.start_position >= -56 and self.end_position < self.start_position:
            dest = ray.Rectangle(x, y-70, self.start_position + 1280 + 56, texture.height)
        else:
            dest = ray.Rectangle(x, y-70, abs(self.end_position) - self.start_position + extra_distance + 57, texture.height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0,0), 0, ray.WHITE)


        if self.end_position < self.start_position and self.end_position >= -56:
            dest = ray.Rectangle(0, y-70, min(self.end_position+75, 1280) + extra_distance, texture.height)
            ray.draw_texture_pro(texture, src, dest, ray.Vector2(0,0), 0, ray.WHITE)

        offset = 150 if self.end_box.is_open else 0
        ray.draw_texture(textures['song_select'][texture_index], self.end_position+75+offset, y-70, ray.WHITE)

        if ((self.start_position <= 594 and self.end_position >= 594) or
            ((self.start_position <= 594 or self.end_position >= 594) and (self.start_position > self.end_position))):
            dest_width = min(300, self.title.texture.width)

            texture = textures['song_select'][GenreBG.HEADER_MAP[self.end_box.texture_index]]
            src = ray.Rectangle(0, 0, texture.width, texture.height)
            dest = ray.Rectangle((1280//2) - (dest_width//2), y-68, dest_width, texture.height)
            ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

            texture = textures['song_select'][GenreBG.HEADER_MAP[self.end_box.texture_index]+1]
            src = ray.Rectangle(0, 0, -texture.width, texture.height)
            dest = ray.Rectangle((1280//2) - (dest_width//2) - (texture.width//2), y-68, texture.width, texture.height)
            ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)
            ray.draw_texture(texture, (1280//2) + (dest_width//2) - (texture.width//2), y-68, ray.WHITE)

            src = ray.Rectangle(0, 0, self.title.texture.width, self.title.texture.height)
            dest = ray.Rectangle((1280//2) - (dest_width//2), y-68, dest_width, self.title.texture.height)
            self.title.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

class YellowBox:
    def __init__(self, name: OutlinedText, is_back: bool, tja: Optional[TJAParser] = None, subtitle: Optional[OutlinedText] = None):
        self.is_diff_select = False
        self.right_x = 803
        self.left_x = 443
        self.top_y = 96
        self.bottom_y = 543
        self.center_width = 332
        self.center_height = 422
        self.edge_height = 32
        self.name = name
        self.subtitle = subtitle
        self.is_back = is_back
        self.tja = tja
        self.anim_created = False
        self.left_out = Animation.create_move(83.33, total_distance=-152, delay=83.33)
        self.right_out = Animation.create_move(83.33, total_distance=145, delay=83.33)
        self.center_out = Animation.create_move(83.33, total_distance=300, delay=83.33)
        self.fade = Animation.create_fade(83.33, initial_opacity=1.0, final_opacity=1.0, delay=83.33)
        self.reset_animations()

    def reset_animations(self):
        self.fade_in = Animation.create_fade(float('inf'), initial_opacity=0.0, final_opacity=1.0, delay=83.33)
        self.left_out_2 = Animation.create_move(float('inf'), total_distance=-213)
        self.right_out_2 = Animation.create_move(float('inf'), total_distance=0)
        self.center_out_2 = Animation.create_move(float('inf'), total_distance=423)
        self.top_y_out = Animation.create_move(float('inf'), total_distance=-62)
        self.center_h_out = Animation.create_move(float('inf'), total_distance=60)

    def create_anim(self):
        self.left_out = Animation.create_move(83.33, total_distance=-152, delay=83.33)
        self.right_out = Animation.create_move(83.33, total_distance=145, delay=83.33)
        self.center_out = Animation.create_move(83.33, total_distance=300, delay=83.33)
        self.fade = Animation.create_fade(83.33, initial_opacity=0.0, final_opacity=1.0, delay=83.33)

    def create_anim_2(self):
        self.left_out_2 = Animation.create_move(116.67, total_distance=-213)
        self.right_out_2 = Animation.create_move(116.67, total_distance=211)
        self.center_out_2 = Animation.create_move(116.67, total_distance=423)

        self.top_y_out = Animation.create_move(133.33, total_distance=-62, delay=self.left_out_2.duration)
        self.center_h_out = Animation.create_move(133.33, total_distance=60, delay=self.left_out_2.duration)

        self.fade_in = Animation.create_fade(116.67, initial_opacity=0.0, final_opacity=1.0, delay=self.left_out_2.duration + self.top_y_out.duration + 16.67)


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
        self.is_diff_select = is_diff_select
        if self.is_diff_select:
            if not self.anim_created:
                self.anim_created = True
                self.create_anim_2()
            self.right_x = 803 + int(self.right_out_2.attribute)
            self.left_x = 443 + int(self.left_out_2.attribute)
            self.top_y = 96 + int(self.top_y_out.attribute)
            self.center_width = 332 + int(self.center_out_2.attribute)
            self.center_height = 422 + int(self.center_h_out.attribute)
        else:
            self.anim_created = False
            self.right_x = 658 + int(self.right_out.attribute)
            self.left_x = 595  + int(self.left_out.attribute)
            self.top_y = 96
            self.center_width = 32 + int(self.center_out.attribute)
            self.center_height = 422

    def draw(self, textures: dict[str, list[ray.Texture]], song_box: SongBox, fade_override: Optional[float], is_ura: bool):
        # Draw corners
        ray.draw_texture(textures['song_select'][235], self.right_x, self.bottom_y, ray.WHITE)  # Bottom right
        ray.draw_texture(textures['song_select'][236], self.left_x, self.bottom_y, ray.WHITE)   # Bottom left
        ray.draw_texture(textures['song_select'][237], self.right_x, self.top_y, ray.WHITE)     # Top right
        ray.draw_texture(textures['song_select'][238], self.left_x, self.top_y, ray.WHITE)      # Top left

        # Edges
        # Bottom edge
        texture = textures['song_select'][231]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(self.left_x + self.edge_height, self.bottom_y, self.center_width, texture.height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        # Right edge
        texture = textures['song_select'][232]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(self.right_x, self.top_y + self.edge_height, texture.width, self.center_height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        # Left edge
        texture = textures['song_select'][233]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(self.left_x, self.top_y + self.edge_height, texture.width, self.center_height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        # Top edge
        texture = textures['song_select'][234]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(self.left_x + self.edge_height, self.top_y, self.center_width, texture.height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        # Center
        texture = textures['song_select'][230]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(self.left_x + self.edge_height, self.top_y + self.edge_height, self.center_width, self.center_height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)


        if self.is_diff_select and self.tja is not None:
            #Back Button
            color = ray.fade(ray.WHITE, self.fade_in.attribute)
            ray.draw_texture(textures['song_select'][153], 314, 110, color)

            #Difficulties
            ray.draw_texture(textures['song_select'][154], 450, 90, color)
            if 0 not in self.tja.metadata.course_data:
                ray.draw_texture(textures['song_select'][161], 450, 90, ray.fade(ray.WHITE, min(self.fade_in.attribute, 0.25)))
            ray.draw_texture(textures['song_select'][182], 565, 90, color)
            if 1 not in self.tja.metadata.course_data:
                ray.draw_texture(textures['song_select'][183], 565, 90, ray.fade(ray.WHITE, min(self.fade_in.attribute, 0.25)))
            ray.draw_texture(textures['song_select'][185], 680, 90, color)
            if 2 not in self.tja.metadata.course_data:
                ray.draw_texture(textures['song_select'][186], 680, 90, ray.fade(ray.WHITE, min(self.fade_in.attribute, 0.25)))
            if is_ura:
                ray.draw_texture(textures['song_select'][190], 795, 90, color)
                ray.draw_texture(textures['song_select'][191], 807, 130, color)
            else:
                ray.draw_texture(textures['song_select'][188], 795, 90, color)
            if 3 not in self.tja.metadata.course_data:
                ray.draw_texture(textures['song_select'][189], 795, 90, ray.fade(ray.WHITE, min(self.fade_in.attribute, 0.25)))

            #Stars
            for course in self.tja.metadata.course_data:
                if course == 4 and not is_ura:
                    continue
                if course == 3 and is_ura:
                    continue
                for j in range(self.tja.metadata.course_data[course].level):
                    ray.draw_texture(textures['song_select'][155], 482+(min(course, 3)*115), 471+(j*-20), color)

        else:
            #Crowns
            fade = self.fade.attribute
            if fade_override is not None:
                fade = min(self.fade.attribute, fade_override)
            color = ray.fade(ray.WHITE, fade)
            if self.is_back:
                ray.draw_texture(textures['song_select'][421], 498, 250, color)
            elif self.tja is not None:
                for diff in self.tja.metadata.course_data:
                    if diff == 4:
                        continue
                    elif diff in song_box.scores and song_box.scores[diff] is not None and song_box.scores[diff][3] == 0:
                        ray.draw_texture(textures['song_select'][160], 473 + (diff*60), 175, color)
                    elif diff in song_box.scores and song_box.scores[diff] is not None and song_box.scores[diff][4] == 1:
                        ray.draw_texture(textures['song_select'][159], 473 + (diff*60), 175, color)
                    ray.draw_texture(textures['song_select'][158], 473 + (diff*60), 175, ray.fade(ray.WHITE, min(fade, 0.25)))

                #EX Data
                if self.tja.ex_data.new_audio:
                    ray.draw_texture(textures['custom'][0], 458, 120, color)
                elif self.tja.ex_data.old_audio:
                    ray.draw_texture(textures['custom'][1], 458, 120, color)
                elif self.tja.ex_data.limited_time:
                    ray.draw_texture(textures['song_select'][418], 458, 120, color)

                #Difficulties
                ray.draw_texture(textures['song_select'][395], 458, 210, color)
                if 0 not in self.tja.metadata.course_data:
                    ray.draw_texture(textures['song_select'][400], 458, 210, ray.fade(ray.WHITE, min(fade, 0.25)))
                ray.draw_texture(textures['song_select'][401], 518, 210, color)
                if 1 not in self.tja.metadata.course_data:
                    ray.draw_texture(textures['song_select'][402], 518, 210, ray.fade(ray.WHITE, min(fade, 0.25)))
                ray.draw_texture(textures['song_select'][403], 578, 210, color)
                if 2 not in self.tja.metadata.course_data:
                    ray.draw_texture(textures['song_select'][404], 578, 210, ray.fade(ray.WHITE, min(fade, 0.25)))
                ray.draw_texture(textures['song_select'][406], 638, 210, color)
                if 3 not in self.tja.metadata.course_data:
                    ray.draw_texture(textures['song_select'][407], 638, 210, ray.fade(ray.WHITE, min(fade, 0.25)))

                #Stars
                for diff in self.tja.metadata.course_data:
                    if diff == 4:
                        continue
                    for j in range(self.tja.metadata.course_data[diff].level):
                        ray.draw_texture(textures['song_select'][396], 474+(diff*60), 490+(j*-17), color)
        if self.is_back:
            texture = textures['song_select'][422]
            x = int(((song_box.position + 55) - texture.width / 2) + (int(self.right_out.attribute)*0.85) + (int(self.right_out_2.attribute)))
            y = self.top_y+35
            ray.draw_texture(texture, x, y, ray.WHITE)
        elif self.name is not None:
            texture = self.name.texture
            x = int(((song_box.position + 55) - texture.width / 2) + (int(self.right_out.attribute)*0.85) + (int(self.right_out_2.attribute)))
            y = self.top_y+35
            src = ray.Rectangle(0, 0, texture.width, texture.height)
            dest = ray.Rectangle(x, y, texture.width, min(texture.height, 417))
            self.name.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)
        if self.subtitle is not None:
            texture = self.subtitle.texture
            x = int(((song_box.position + 10) - texture.width / 2) + (int(self.right_out.attribute)*0.85) + (int(self.right_out_2.attribute)))
            y = self.bottom_y - min(texture.height, 410) + 10 + int(self.top_y_out.attribute)
            src = ray.Rectangle(0, 0, texture.width, texture.height)
            dest = ray.Rectangle(x, y, texture.width, min(texture.height, 410))
            self.subtitle.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

class UraSwitchAnimation:
    def __init__(self, is_backwards: bool) -> None:
        forwards_animation = ((0, 32, 166), (32, 80, 167), (80, 112, 168), (112, 133, 169))
        backwards_animation = ((0, 32, 169), (32, 80, 170), (80, 112, 171), (112, 133, 166))
        if is_backwards:
            self.texture_change = Animation.create_texture_change(133, textures=backwards_animation)
        else:
            self.texture_change = Animation.create_texture_change(133, textures=forwards_animation)
        self.fade_out = Animation.create_fade(166, delay=133)
    def update(self, current_ms: float):
        self.texture_change.update(current_ms)
        self.fade_out.update(current_ms)
    def draw(self, textures: dict[str, list[ray.Texture]]):
        ray.draw_texture(textures['song_select'][self.texture_change.attribute], 815, 134, ray.fade(ray.WHITE, self.fade_out.attribute))

class Transition:
    def __init__(self, screen_height: int) -> None:
        self.is_finished = False
        self.rainbow_up = Animation.create_move(266, start_position=0, total_distance=screen_height + global_data.textures['scene_change_rainbow'][2].height, ease_in='cubic')
        self.chara_down = None
    def update(self, current_time_ms: float):
        self.rainbow_up.update(current_time_ms)
        if self.rainbow_up.is_finished and self.chara_down is None:
            self.chara_down = Animation.create_move(33, start_position=0, total_distance=30)

        if self.chara_down is not None:
            self.chara_down.update(current_time_ms)
            self.is_finished = self.chara_down.is_finished

    def draw(self, screen_height: int):
        ray.draw_texture(global_data.textures['scene_change_rainbow'][2], 0, screen_height - int(self.rainbow_up.attribute), ray.WHITE)
        texture = global_data.textures['scene_change_rainbow'][0]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(0, screen_height - int(self.rainbow_up.attribute) + global_data.textures['scene_change_rainbow'][2].height, texture.width, screen_height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)
        texture = global_data.textures['scene_change_rainbow'][3]
        offset = 0
        if self.chara_down is not None:
            offset = int(self.chara_down.attribute)
        ray.draw_texture(texture, 76, 816 - int(self.rainbow_up.attribute) + offset, ray.WHITE)

class FileSystemItem:
    GENRE_MAP = {
        'J-POP': 555,
        'アニメ': 560,
        'どうよう': 565,
        'バラエティー': 570,
        'クラシック': 575,
        'ゲームミュージック': 580,
        'ナムコオリジナル': 585,
        'VOCALOID': 615,
    }
    """Base class for files and directories in the navigation system"""
    def __init__(self, path: Path, name: str):
        self.path = path
        self.selected = False

class Directory(FileSystemItem):
    """Represents a directory in the navigation system"""
    def __init__(self, path: Path, name: str, texture_index: int, has_box_def=False, to_root=False, back=False, tja_count=0, box_texture=None):
        super().__init__(path, name)
        self.has_box_def = has_box_def
        self.to_root = to_root
        self.back = back
        self.tja_count = tja_count

        if self.to_root or self.back:
            texture_index = 552

        self.box = SongBox(name, texture_index, True, tja_count=tja_count, box_texture=box_texture)

class SongFile(FileSystemItem):
    """Represents a song file (TJA) in the navigation system"""
    def __init__(self, path: Path, name: str, texture_index: int, tja=None):
        super().__init__(path, name)
        self.tja = tja or TJAParser(path)
        title = self.tja.metadata.title.get(global_data.config['general']['language'].lower(), self.tja.metadata.title['en'])
        self.box = SongBox(title, texture_index, False, tja=self.tja)
        self.box.get_scores()

class FileNavigator:
    """Manages navigation through pre-generated Directory and SongFile objects"""
    def __init__(self, root_dirs: list[str]):
        # Handle both single path and list of paths
        if isinstance(root_dirs, (list, tuple)):
            self.root_dirs = [Path(p) if not isinstance(p, Path) else p for p in root_dirs]
        else:
            self.root_dirs = [Path(root_dirs) if not isinstance(root_dirs, Path) else root_dirs]

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
        self.selected_index = 0
        self.history = []
        self.box_open = False
        self.genre_bg = None

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

            if has_box_def:
                name, texture_index = self._parse_box_def(dir_path)
                box_png_path = dir_path / "box.png"
                if box_png_path.exists():
                    box_texture = ray.load_texture(str(box_png_path))

            # Count TJA files for this directory
            tja_count = self._count_tja_files(dir_path)

            # Create Directory object
            directory_obj = Directory(
                dir_path, name, texture_index,
                has_box_def=has_box_def,
                tja_count=tja_count,
                box_texture=box_texture
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
                    try:
                        song_obj = SongFile(tja_path, tja_path.name, texture_index)
                        self.all_song_files[song_key] = song_obj
                    except Exception as e:
                        print(f"Error creating SongFile for {tja_path}: {e}")
                        continue

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
                                song_obj = SongFile(tja_path, tja_path.name, 620)
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
        tja_files = []

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
        tja_files = []

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
        texture_index = 620
        name = path.name

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
        except Exception as e:
            print(f"Error parsing box.def in {path}: {e}")

        return name, texture_index

    def _read_song_list(self, path: Path):
        """Read and process song_list.txt file"""
        tja_files = []
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

                if song_hash.song_hashes is not None:
                    if hash_val in song_hash.song_hashes:
                        file_path = Path(song_hash.song_hashes[hash_val]["file_path"])
                        if file_path.exists():
                            tja_files.append(file_path)
                    else:
                        # Try to find by title and subtitle
                        for key, value in song_hash.song_hashes.items():
                            if (value["title"]["en"] == title and
                                value["subtitle"]["en"][2:] == subtitle and
                                Path(value["file_path"]).exists()):
                                hash_val = key
                                tja_files.append(Path(song_hash.song_hashes[hash_val]["file_path"]))
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
            back_dir = Directory(self.current_dir.parent, "", 552, back=True)
            if not has_children:
                start_box = back_dir.box
            self.items.insert(self.selected_index, back_dir)
        elif not self.in_root_selection:
            to_root_dir = Directory(Path(), "", 552, to_root=True)
            self.items.append(to_root_dir)

        # Add pre-generated content for this directory
        if dir_key in self.directory_contents:
            content_items = self.directory_contents[dir_key]

            i = 1
            for item in content_items:
                if isinstance(item, SongFile):
                    if i % 10 == 0 and i != 0:
                        back_dir = Directory(self.current_dir.parent, "", 552, back=True)
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

    def get_stats(self):
        """Get statistics about the pre-generated objects"""
        song_count_by_dir = {}
        for dir_path, items in self.directory_contents.items():
            song_count_by_dir[dir_path] = len([item for item in items if isinstance(item, SongFile)])

        return {
            'total_directories': len(self.all_directories),
            'total_songs': len(self.all_song_files),
            'root_items': len(self.root_items),
            'directories_with_content': len(self.directory_contents),
            'songs_by_directory': song_count_by_dir
        }
