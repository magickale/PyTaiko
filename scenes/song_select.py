import os
import sqlite3
from pathlib import Path

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.tja import TJAParser
from libs.utils import (
    OutlinedText,
    get_config,
    get_current_ms,
    global_data,
    load_all_textures_from_zip,
    session_data,
)


class SongSelectScreen:
    BOX_CENTER = 444
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.song_name_textures: list[OutlinedText] = []
        self.selected_song = 0
        self.selected_difficulty = 0
        self.song_boxes: list[SongBox] = []
        self.screen_init = False

        i = 0
        for dirpath, dirnames, filenames in os.walk(f'{get_config()["paths"]["tja_path"]}'):
            for filename in filenames:
                if filename.endswith(".tja"):
                    position = -56 + (100*i)
                    if position == SongSelectScreen.BOX_CENTER:
                        position += 150
                    elif position > SongSelectScreen.BOX_CENTER:
                        position += 300
                    self.song_boxes.append(SongBox(dirpath, position))
                    i += 1


    def load_textures(self):
        self.textures = load_all_textures_from_zip(Path('Graphics/lumendata/song_select.zip'))

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(str(sounds_dir / "inst_00_don.wav"))
        self.sound_kat = audio.load_sound(str(sounds_dir / "inst_00_katsu.wav"))

    def on_screen_start(self):
        if not self.screen_init:
            self.load_textures()
            self.load_sounds()
            self.game_transition = None
            self.move_away = Animation.create_move(float('inf'))
            self.diff_fade_out = Animation.create_fade(0, final_opacity=1.0)
            self.text_fade_out = None
            self.text_fade_in = None
            self.screen_init = True
            self.is_difficulty_select = False
            self.background_move = Animation.create_move(15000, start_position=0, total_distance=1280)

    def on_screen_end(self):
        self.screen_init = False
        curr_box = self.song_boxes[0]
        for box in self.song_boxes:
            if box.is_open:
                curr_box = box
            box.reset()
        global_data.selected_song = curr_box.tja_path
        session_data.selected_difficulty = self.selected_difficulty
        for zip in self.textures:
            for texture in self.textures[zip]:
                ray.unload_texture(texture)
        return "GAME"

    def update_song_select(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            audio.play_sound(self.sound_don)
            self.move_away = Animation.create_move(233, total_distance=500)
            self.diff_fade_out = Animation.create_fade(83)
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_LEFT):
            audio.play_sound(self.sound_kat)
            for box in self.song_boxes:
                box.move_left()
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_RIGHT):
            audio.play_sound(self.sound_kat)
            for box in self.song_boxes:
                box.move_right()

    def update_difficulty_select(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            if self.selected_difficulty == -1:
                self.is_difficulty_select = False
                self.move_away = Animation.create_move(float('inf'))
                self.diff_fade_out = Animation.create_fade(0, final_opacity=1.0)
                self.text_fade_out = None
                self.text_fade_in = None
                for box in self.song_boxes:
                    if box.yellow_box is not None:
                        box.yellow_box.reset_animations()
            else:
                audio.play_sound(self.sound_don)
                self.game_transition = Transition(self.height)
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_LEFT):
            audio.play_sound(self.sound_kat)
            if self.selected_difficulty >= 0:
                self.selected_difficulty = (self.selected_difficulty - 1)
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_RIGHT):
            audio.play_sound(self.sound_kat)
            if self.selected_difficulty < 4:
                self.selected_difficulty = (self.selected_difficulty + 1)

    def update(self):
        self.on_screen_start()
        if self.background_move.is_finished:
            self.background_move = Animation.create_move(15000, start_position=0, total_distance=1280)
        self.background_move.update(get_current_ms())

        if self.move_away.is_finished and self.text_fade_out is None:
            self.text_fade_out = Animation.create_fade(33)
            self.text_fade_in = Animation.create_fade(33, initial_opacity=0.0, final_opacity=1.0, delay=self.text_fade_out.duration)
        self.move_away.update(get_current_ms())

        if self.text_fade_out is not None:
            self.text_fade_out.update(get_current_ms())
            if self.text_fade_out.is_finished:
                self.is_difficulty_select = True

        if self.text_fade_in is not None:
            self.text_fade_in.update(get_current_ms())

        self.diff_fade_out.update(get_current_ms())

        if self.is_difficulty_select:
            self.update_difficulty_select()
        else:
            self.update_song_select()
        for box in self.song_boxes:
            box.update(self.is_difficulty_select)

        if self.game_transition is not None:
            self.game_transition.update(get_current_ms())
            if self.game_transition.is_finished:
                return self.on_screen_end()


    def draw_song_select(self):
        for box in self.song_boxes:
            if box.position <= 500:
                box.draw(box.position - int(self.move_away.attribute), 95, 620, self.textures, int(self.diff_fade_out.attribute))
            else:
                box.draw(box.position + int(self.move_away.attribute), 95, 620, self.textures, int(self.diff_fade_out.attribute))

    def draw_selector(self):
        if self.selected_difficulty == -1:
            ray.draw_texture(self.textures['song_select'][133], 314, 110, ray.WHITE)
        else:
            ray.draw_texture(self.textures['song_select'][140], 450 + (self.selected_difficulty * 115), 7, ray.WHITE)
            ray.draw_texture(self.textures['song_select'][131], 461 + (self.selected_difficulty * 115), 132, ray.WHITE)

    def draw_difficulty_select(self):
        for box in self.song_boxes:
            if box.is_open:
                box.draw(box.position, 95, 620, self.textures, int(self.diff_fade_out.attribute))
        self.draw_selector()

    def draw(self):
        texture = self.textures['song_select'][784]
        for i in range(0, texture.width * 4, texture.width):
            ray.draw_texture(self.textures['song_select'][784], i - int(self.background_move.attribute), 0, ray.WHITE)
        if self.is_difficulty_select:
            self.draw_difficulty_select()
            fade = ray.WHITE
            if self.text_fade_in is not None:
                fade = ray.fade(ray.WHITE, self.text_fade_in.attribute)
            ray.draw_texture(self.textures['song_select'][192], 5, 5, fade)
        else:
            self.draw_song_select()
            fade = ray.WHITE
            if self.text_fade_out is not None:
                fade = ray.fade(ray.WHITE, self.text_fade_out.attribute)
            ray.draw_texture(self.textures['song_select'][244], 5, 5, fade)
        ray.draw_texture(self.textures['song_select'][394], 0, self.height - self.textures['song_select'][394].height, ray.WHITE)

        if self.game_transition is not None:
            self.game_transition.draw(self.height)

class SongBox:
    def __init__(self, tja_path: str, position: int):
        self.tja_path = tja_path
        self.scores = dict()
        self.position = position
        self.start_position = position
        tja = TJAParser(tja_path)
        self.course_data = tja.get_metadata()
        for diff in self.course_data[8].keys():
            self.scores[diff] = self._get_scores(tja, diff)
        self.is_open = False
        self.name = None
        self.yellow_box = None
        self.move = Animation.create_move(0)
        self.wait = 0
        self.update(False)

    def reset(self):
        self.yellow_box = YellowBox(self.name)

    def _load_font_for_text(self, text: str) -> ray.Font:
        codepoint_count = ray.ffi.new('int *', 0)
        unique_codepoints = set(text)
        codepoints = ray.load_codepoints(''.join(unique_codepoints), codepoint_count)
        return ray.load_font_ex(str(Path('Graphics/Modified-DFPKanteiryu-XB.ttf')), 40, codepoints, 0)

    def _get_scores(self, tja: TJAParser, difficulty: int):
        with sqlite3.connect('scores.db') as con:
            cursor = con.cursor()
            hash = tja.hash_note_data(tja.data_to_notes(difficulty)[0])
            check_query = "SELECT score, good, ok, bad FROM Scores WHERE hash = ? LIMIT 1"
            cursor.execute(check_query, (hash,))
            result = cursor.fetchone()
        return result

    def move_left(self):
        if not self.move.is_finished:
            self.position = self.start_position
            self.move = Animation.create_move(0)
            return
        self.start_position = self.position
        self.move = Animation.create_move(66.67, start_position=0, total_distance=100)
        if self.is_open:
            self.move.total_distance = 250
        elif self.position + self.move.total_distance == SongSelectScreen.BOX_CENTER:
            self.move.total_distance = 250
        elif SongSelectScreen.BOX_CENTER < self.position + self.move.total_distance < SongSelectScreen.BOX_CENTER + 300:
            self.move.total_distance = 400

    def move_right(self):
        if not self.move.is_finished:
            self.position = self.start_position
            self.move = Animation.create_move(0)
            return
        self.start_position = self.position
        self.move = Animation.create_move(66.67, start_position=0, total_distance=-100)
        if self.is_open:
            self.move.total_distance = -250
        elif self.position + (self.move.total_distance - 300) == SongSelectScreen.BOX_CENTER:
            self.move.total_distance = -250
        elif SongSelectScreen.BOX_CENTER < self.position + self.move.total_distance < SongSelectScreen.BOX_CENTER + 300:
            self.move.total_distance = -400

    def update(self, is_diff_select):
        self.is_diff_select = is_diff_select
        if self.yellow_box is not None:
            self.yellow_box.update(is_diff_select)
        self.move.update(get_current_ms())
        self.position = self.start_position + int(self.move.attribute)
        is_open_prev = self.is_open
        self.is_open = self.position == SongSelectScreen.BOX_CENTER + 150
        if not is_open_prev and self.is_open:
            if self.yellow_box is not None:
                self.wait = get_current_ms()
                self.yellow_box.create_anim()

        if self.name is None and 0 <= self.position <= 1280:
            name = self.course_data[0]
            font = self._load_font_for_text(name)
            self.name = OutlinedText(font, name, 40, ray.WHITE, ray.BLACK, outline_thickness=4, vertical=True)
            self.yellow_box = YellowBox(self.name)

    def _draw_closed(self, x: int, y: int, texture_index: int, textures):
        ray.draw_texture(textures['song_select'][texture_index+1], x, y, ray.WHITE)
        for i in range(0, textures['song_select'][texture_index].width * 4, textures['song_select'][texture_index].width):
            ray.draw_texture(textures['song_select'][texture_index], (x+32)+i, y, ray.WHITE)
        ray.draw_texture(textures['song_select'][texture_index+2], x+64, y, ray.WHITE)
        ray.draw_texture(textures['song_select'][texture_index+3], x+12, y+16, ray.WHITE)

        if self.name is not None:
            src = ray.Rectangle(0, 0, self.name.texture.width, self.name.texture.height)
            dest = ray.Rectangle(x + 47 - int(self.name.texture.width / 2), y+35, self.name.texture.width, min(self.name.texture.height, 417))
            self.name.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

    def draw(self, x: int, y: int, texture_index: int, textures, fade_override=None):
        if self.is_open and get_current_ms() >= self.wait + 83.33:
            if self.yellow_box is not None:
                self.yellow_box.draw(textures, self, fade_override)
        else:
            self._draw_closed(x, y, texture_index, textures)


class YellowBox:
    def __init__(self, name):
        self.is_diff_select = False
        self.right_x = 803
        self.left_x = 443
        self.top_y = 96
        self.bottom_y = 543
        self.center_width = 332
        self.center_height = 422
        self.edge_height = 32
        self.name = name
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


    def update(self, is_diff_select):
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

    def draw(self, textures: dict[str, list[ray.Texture]], song_box: SongBox, fade_override):

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


        if self.is_diff_select:
            #Back Button
            color = ray.fade(ray.WHITE, self.fade_in.attribute)
            ray.draw_texture(textures['song_select'][153], 314, 110, color)

            #Difficulties
            ray.draw_texture(textures['song_select'][154], 450, 90, color)
            ray.draw_texture(textures['song_select'][182], 565, 90, color)
            ray.draw_texture(textures['song_select'][185], 680, 90, color)
            ray.draw_texture(textures['song_select'][188], 795, 90, color)

            for i in range(4):
                try:
                    for j in range(song_box.course_data[8][i][0]):
                        ray.draw_texture(textures['song_select'][155], 482+(i*115), 471+(j*-20), color)
                except:
                    pass

        else:
            #Crowns
            fade = self.fade.attribute
            if fade_override is not None:
                fade = min(self.fade.attribute, fade_override)
            color = ray.fade(ray.WHITE, fade)
            for i in range(4):
                if i in song_box.scores and song_box.scores[i] is not None and song_box.scores[i][3] == 0:
                    ray.draw_texture(textures['song_select'][160], 473 + (i*60), 175, color)
                ray.draw_texture(textures['song_select'][158], 473 + (i*60), 175, ray.fade(color, min(fade, 0.25)))

            #Difficulties
            ray.draw_texture(textures['song_select'][395], 458, 210, color)
            ray.draw_texture(textures['song_select'][401], 518, 210, color)
            ray.draw_texture(textures['song_select'][403], 578, 210, color)
            ray.draw_texture(textures['song_select'][406], 638, 210, color)

            #Stars
            for i in range(4):
                try:
                    for j in range(song_box.course_data[8][i][0]):
                        ray.draw_texture(textures['song_select'][396], 474+(i*60), 490+(j*-17), color)
                except:
                    pass

        if self.name is not None:
            texture = self.name.texture
            src = ray.Rectangle(0, 0, texture.width, texture.height)
            dest = ray.Rectangle(((song_box.position + 47) - texture.width / 2) + (int(self.right_out.attribute)*0.85) + (int(self.right_out_2.attribute)), self.top_y+35, texture.width, min(texture.height, 417))
            self.name.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

class Transition:
    def __init__(self, screen_height) -> None:
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

    def draw(self, screen_height):
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
