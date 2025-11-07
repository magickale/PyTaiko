from dataclasses import dataclass
import json
import logging
from pathlib import Path
import random
from typing import Optional, Union
from libs.audio import audio
from libs.animation import Animation, MoveAnimation
from libs.tja import TJAParser, test_encodings
from libs.texture import tex
from libs.utils import OutlinedText, get_current_ms, global_data
from datetime import datetime, timedelta
import sqlite3
import pyray as ray

BOX_CENTER = 444

logger = logging.getLogger(__name__)

class SongBox:
    """A box for the song select screen."""
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
        if self.is_back:
            for i in range(1, 16):
                if audio.is_sound_playing(f'genre_voice_{i}'):
                    audio.stop_sound(f'genre_voice_{i}')
        self.name = None
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
        self.is_favorite = False

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
                hash_values = [self.hash[diff] for diff in self.tja.metadata.course_data if diff in self.hash]
                placeholders = ','.join('?' * len(hash_values))

                batch_query = f"""
                    SELECT hash, score, good, ok, bad, drumroll, clear
                    FROM Scores
                    WHERE hash IN ({placeholders})
                """
                cursor.execute(batch_query, hash_values)

                hash_to_score = {row[0]: row[1:] for row in cursor.fetchall()}

                for diff in self.tja.metadata.course_data:
                    if diff not in self.hash:
                        continue
                    diff_hash = self.hash[diff]
                    self.scores[diff] = hash_to_score.get(diff_hash)
                self.score_history = None

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
            if self.is_open or self.target_position == BOX_CENTER + 150:
                self.move.total_distance = 250 * direction
            self.start_position = self.position
        if self.move is not None:
            self.move.update(get_current_ms())
            self.position = self.start_position + int(self.move.attribute)
            if self.move.is_finished:
                self.position = self.target_position
                self.move = None
                if not (-56 <= self.position <= 1280):
                    self.reset()

    def update(self, is_diff_select: bool):
        current_time = get_current_ms()
        self.is_diff_select = is_diff_select
        is_open_prev = self.is_open
        self.move_box()
        self.is_open = self.position == BOX_CENTER + 150

        if not (-56 <= self.position <= 1280):
            return
        if self.yellow_box is not None:
            self.yellow_box.update(is_diff_select)

        if self.history_wait == 0:
            self.history_wait = current_time

        if self.score_history is None and {k: v for k, v in self.scores.items() if v is not None}:
            self.score_history = ScoreHistory(self.scores, current_time)

        if not is_open_prev and self.is_open:
            if self.tja is not None or self.is_back:
                self.yellow_box = YellowBox(self.name, self.is_back, tja=self.tja)
                self.yellow_box.create_anim()
            else:
                self.hori_name = OutlinedText(self.text_name, 40, ray.WHITE, outline_thickness=5)
                self.open_anim.start()
                self.open_fade.start()
            self.wait = current_time
            if current_time >= self.history_wait + 3000:
                self.history_wait = current_time
            if self.tja is None and self.texture_index != 17 and not audio.is_sound_playing('voice_enter'):
                audio.play_sound(f'genre_voice_{self.texture_index}', 'voice')
        elif not self.is_open and is_open_prev and audio.is_sound_playing(f'genre_voice_{self.texture_index}'):
            audio.stop_sound(f'genre_voice_{self.texture_index}')
        if self.tja_count is not None and self.tja_count > 0 and self.tja_count_text is None:
            self.tja_count_text = OutlinedText(str(self.tja_count), 35, ray.WHITE, outline_thickness=5)#, horizontal_spacing=1.2)
        if self.box_texture is None and self.box_texture_path is not None:
            self.box_texture = ray.load_texture(self.box_texture_path)

        self.open_anim.update(current_time)
        self.open_fade.update(current_time)

        if self.name is None:
            self.name = OutlinedText(self.text_name, 40, ray.WHITE, outline_thickness=5, vertical=True)

        if self.score_history is not None:
            self.score_history.update(current_time)


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
            return
        elif self.name is not None:
            self.name.draw(outline_color=SongBox.OUTLINE_MAP.get(self.name_texture_index, ray.Color(101, 0, 82, 255)), x=x + 47 - int(self.name.texture.width / 2), y=y+35, y2=min(self.name.texture.height, 417)-self.name.texture.height)

        if self.tja is not None and self.tja.ex_data.new:
            tex.draw_texture('yellow_box', 'ex_data_new_song_balloon', x=x, y=y)
        valid_scores = {k: v for k, v in self.scores.items() if v is not None}
        if valid_scores:
            highest_key = max(valid_scores.keys())
            score = self.scores[highest_key]
            if score and ((score[5] == 2 and score[2] == 0) or (score[2] == 0 and score[3] == 0)):
                tex.draw_texture('yellow_box', 'crown_dfc', x=x, y=y, frame=min(4, highest_key))
            elif score and ((score[5] == 2) or (score[3] == 0)):
                tex.draw_texture('yellow_box', 'crown_fc', x=x, y=y, frame=min(4, highest_key))
            elif score and score[5] >= 1:
                tex.draw_texture('yellow_box', 'crown_clear', x=x, y=y, frame=min(4, highest_key))
        if self.crown: #Folder lamp
            highest_crown = max(self.crown)
            if self.crown[highest_crown] == 'DFC':
                tex.draw_texture('yellow_box', 'crown_dfc', x=x, y=y, frame=min(4, highest_crown))
            elif self.crown[highest_crown] == 'FC':
                tex.draw_texture('yellow_box', 'crown_fc', x=x, y=y, frame=min(4, highest_crown))
            else:
                tex.draw_texture('yellow_box', 'crown_clear', x=x, y=y, frame=min(4, highest_crown))

    def _draw_open(self, x: int, y: int, fade_override: Optional[float]):
        color = ray.WHITE
        if fade_override is not None:
            color = ray.fade(ray.WHITE, fade_override)
        if self.hori_name is not None and self.open_anim.attribute >= 100:
            tex.draw_texture('box', 'folder_top_edge', x=x, y=y - self.open_anim.attribute, color=color, mirror='horizontal', frame=self.texture_index)
            tex.draw_texture('box', 'folder_top', x=x, y=y - self.open_anim.attribute, color=color, frame=self.texture_index)
            tex.draw_texture('box', 'folder_top_edge', x=x+268, y=y - self.open_anim.attribute, color=color, frame=self.texture_index)
            dest_width = min(300, self.hori_name.texture.width)
            self.hori_name.draw(outline_color=ray.BLACK, x=(x + 48) - (dest_width//2), y=y + 107 - self.open_anim.attribute, x2=dest_width-self.hori_name.texture.width, color=color)

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
            self.tja_count_text.draw(outline_color=ray.BLACK, x=560 - (dest_width//2), y=126, x2=dest_width-self.tja_count_text.texture.width, color=color)
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
    """A song box when it is opened."""
    def __init__(self, name: Optional[OutlinedText], is_back: bool, tja: Optional[TJAParser] = None, is_dan: bool = False):
        self.is_diff_select = False
        self.name = name
        self.is_back = is_back
        self.tja = tja
        self.is_dan = is_dan
        self.subtitle = None
        if self.tja is not None:
            subtitle_text = self.tja.metadata.subtitle.get(global_data.config['general']['language'], '')
            font_size = 30 if len(subtitle_text) < 30 else 20
            self.subtitle = OutlinedText(subtitle_text, font_size, ray.WHITE, outline_thickness=5, vertical=True)

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
        current_time = get_current_ms()
        self.left_out.update(current_time)
        self.right_out.update(current_time)
        self.center_out.update(current_time)
        self.fade.update(current_time)
        self.fade_in.update(current_time)
        self.left_out_2.update(current_time)
        self.right_out_2.update(current_time)
        self.center_out_2.update(current_time)
        self.top_y_out.update(current_time)
        self.center_h_out.update(current_time)
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
            elif diff in song_box.scores and song_box.scores[diff] is not None and ((song_box.scores[diff][4] == 2 and song_box.scores[diff][2] == 0) or (song_box.scores[diff][2] == 0 and song_box.scores[diff][3] == 0)):
                tex.draw_texture('yellow_box', 's_crown_dfc', x=(diff*60), color=color)
            elif diff in song_box.scores and song_box.scores[diff] is not None and ((song_box.scores[diff][4] == 2) or (song_box.scores[diff][3] == 0)):
                tex.draw_texture('yellow_box', 's_crown_fc', x=(diff*60), color=color)
            elif diff in song_box.scores and song_box.scores[diff] is not None and song_box.scores[diff][4] >= 1:
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
        if song_box.is_favorite:
            tex.draw_texture('yellow_box', f'favorite_{global_data.player_num}p', color=color)

        for i in range(4):
            tex.draw_texture('yellow_box', 'difficulty_bar', frame=i, x=(i*60), color=color)
            if i not in self.tja.metadata.course_data:
                tex.draw_texture('yellow_box', 'difficulty_bar_shadow', frame=i, x=(i*60), fade=min(fade, 0.25))

        for diff in self.tja.metadata.course_data:
            if diff >= 4:
                continue
            for j in range(self.tja.metadata.course_data[diff].level):
                tex.draw_texture('yellow_box', 'star', x=(diff*60), y=(j*-17), color=color)
            if self.tja.metadata.course_data[diff].is_branching and (get_current_ms() // 1000) % 2 == 0:
                tex.draw_texture('yellow_box', 'branch_indicator', x=(diff*60), color=color)

    def _draw_tja_data_diff(self, is_ura: bool, song_box: Optional[SongBox] = None):
        if self.tja is None:
            return
        tex.draw_texture('diff_select', 'back', fade=self.fade_in.attribute)
        tex.draw_texture('diff_select', 'option', fade=self.fade_in.attribute)
        tex.draw_texture('diff_select', 'neiro', fade=self.fade_in.attribute)

        for diff in self.tja.metadata.course_data:
            if song_box is None:
                continue
            if diff >= 4:
                continue
            elif diff in song_box.scores and song_box.scores[diff] is not None and ((song_box.scores[diff][4] == 2 and song_box.scores[diff][2] == 0) or (song_box.scores[diff][2] == 0 and song_box.scores[diff][3] == 0)):
                tex.draw_texture('yellow_box', 's_crown_dfc', x=(diff*115)+8, y=-120, fade=self.fade_in.attribute)
            elif diff in song_box.scores and song_box.scores[diff] is not None and ((song_box.scores[diff][4] == 2) or (song_box.scores[diff][3] == 0)):
                tex.draw_texture('yellow_box', 's_crown_fc', x=(diff*115)+8, y=-120, fade=self.fade_in.attribute)
            elif diff in song_box.scores and song_box.scores[diff] is not None and song_box.scores[diff][4] >= 1:
                tex.draw_texture('yellow_box', 's_crown_clear', x=(diff*115)+8, y=-120, fade=self.fade_in.attribute)
            tex.draw_texture('yellow_box', 's_crown_outline', x=(diff*115)+8, y=-120, fade=min(self.fade_in.attribute, 0.25))

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
            if self.tja.metadata.course_data[course].is_branching and (get_current_ms() // 1000) % 2 == 0:
                if course == 4:
                    name = 'branch_indicator_ura'
                else:
                    name = 'branch_indicator_diff'
                tex.draw_texture('yellow_box', name, x=min(course, 3)*115, fade=self.fade_in.attribute)

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
            self.name.draw(outline_color=ray.BLACK, x=x + 30, y=35 + self.top_y_out.attribute, y2=min(texture.height, 417)-texture.height, color=ray.WHITE)
        if self.subtitle is not None:
            texture = self.subtitle.texture
            y = self.bottom_y - min(texture.height, 410) + 10 + self.top_y_out.attribute - self.top_y_out.start_position
            self.subtitle.draw(outline_color=ray.BLACK, x=x-15, y=y, y2=min(texture.height, 410)-texture.height)

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

    def draw(self, song_box: Optional[SongBox], fade_override: Optional[float], is_ura: bool):
        self._draw_yellow_box()
        if self.is_dan:
            return
        if self.is_diff_select and self.tja is not None:
            self._draw_tja_data_diff(is_ura, song_box)
        else:
            fade = self.fade.attribute
            if fade_override is not None:
                fade = min(self.fade.attribute, fade_override)
            if self.is_back:
                tex.draw_texture('box', 'back_graphic', fade=fade)
            self._draw_tja_data(song_box, ray.fade(ray.WHITE, fade), fade)

        self._draw_text(song_box)

class DanBox:
    def __init__(self, title: str, color: int, songs: list[tuple[TJAParser, int, int]], exams: list['Exam']):
        self.position = -11111
        self.start_position = -1
        self.target_position = -1
        self.move = None
        self.is_open = False
        self.is_back = False
        self.title = title
        self.color = color
        self.songs = songs
        self.exams = exams
        self.song_text: list[tuple[OutlinedText, OutlinedText]] = []
        self.total_notes = 0
        for song, genre_index, difficulty in self.songs:
            notes, branch_m, branch_e, branch_n = song.notes_to_position(difficulty)
            self.total_notes += sum(1 for note in notes.play_notes if note.type < 5)
            for branch in branch_m:
                self.total_notes += sum(1 for note in branch.play_notes if note.type < 5)
            for branch in branch_e:
                self.total_notes += sum(1 for note in branch.play_notes if note.type < 5)
            for branch in branch_n:
                self.total_notes += sum(1 for note in branch.play_notes if note.type < 5)
        self.name = None
        self.hori_name = None
        self.yellow_box = None

    def move_box(self):
        if self.position != self.target_position and self.move is None:
            if self.position < self.target_position:
                direction = 1
            else:
                direction = -1
            if abs(self.target_position - self.position) > 250:
                direction *= -1
            self.move = Animation.create_move(83.3*2, start_position=0, total_distance=300 * direction, ease_out='cubic')
            self.move.start()
            if self.is_open or self.target_position == BOX_CENTER + 150:
                self.move.total_distance = 450 * direction
            self.start_position = self.position
        if self.move is not None:
            self.move.update(get_current_ms())
            self.position = self.start_position + int(self.move.attribute)
            if self.move.is_finished:
                self.position = self.target_position
                self.move = None
                if not (-56 <= self.position <= 1280):
                    self.reset()

    def reset(self):
        if self.name is not None:
            self.name.unload()
            self.name = None

    def get_text(self):
        if self.name is None:
            self.name = OutlinedText(self.title, 40, ray.WHITE, vertical=True)
            self.hori_name = OutlinedText(self.title, 40, ray.WHITE)
        if self.is_open and not self.song_text:
            for song, genre, difficulty in self.songs:
                title = song.metadata.title.get(global_data.config["general"]["language"], song.metadata.title["en"])
                subtitle = song.metadata.subtitle.get(global_data.config["general"]["language"], "")
                title_text = OutlinedText(title, 40, ray.WHITE, vertical=True)
                font_size = 30 if len(subtitle) < 30 else 20
                subtitle_text = OutlinedText(subtitle, font_size, ray.WHITE, vertical=True)
                self.song_text.append((title_text, subtitle_text))

    def update(self, is_diff_select: bool):
        self.move_box()
        self.get_text()
        is_open_prev = self.is_open
        self.is_open = self.position == BOX_CENTER + 150
        if not is_open_prev and self.is_open:
            self.yellow_box = YellowBox(self.name, self.is_back, is_dan=True)
            self.yellow_box.create_anim()

        if self.yellow_box is not None:
            self.yellow_box.update(True)

    def _draw_exam_box(self):
        tex.draw_texture('yellow_box', 'exam_box_bottom_right')
        tex.draw_texture('yellow_box', 'exam_box_bottom_left')
        tex.draw_texture('yellow_box', 'exam_box_top_right')
        tex.draw_texture('yellow_box', 'exam_box_top_left')
        tex.draw_texture('yellow_box', 'exam_box_bottom')
        tex.draw_texture('yellow_box', 'exam_box_right')
        tex.draw_texture('yellow_box', 'exam_box_left')
        tex.draw_texture('yellow_box', 'exam_box_top')
        tex.draw_texture('yellow_box', 'exam_box_center')
        tex.draw_texture('yellow_box', 'exam_header')

        for i, exam in enumerate(self.exams):
            tex.draw_texture('yellow_box', 'judge_box', y=(i*83))
            tex.draw_texture('yellow_box', 'exam_' + self.exams[i].type, y=(i*83))
            counter = str(self.exams[i].red)
            margin = 20
            if self.exams[i].type == 'gauge':
                tex.draw_texture('yellow_box', 'exam_percent', y=(i*83))
                offset = -8
            else:
                offset = 0
            for j in range(len(counter)):
                tex.draw_texture('yellow_box', 'judge_num', frame=int(counter[j]), x=offset-(len(counter) - j) * margin, y=(i*83))

            if self.exams[i].range == 'more':
                tex.draw_texture('yellow_box', 'exam_more', x=(offset*-1.7), y=(i*83))
            elif self.exams[i].range == 'less':
                tex.draw_texture('yellow_box', 'exam_less', x=(offset*-1.7), y=(i*83))

    def _draw_closed(self, x: int, y: int):
        tex.draw_texture('box', 'folder', frame=self.color, x=x)
        if self.name is not None:
            self.name.draw(outline_color=ray.BLACK, x=x + 47 - int(self.name.texture.width / 2), y=y+35, y2=min(self.name.texture.height, 417)-self.name.texture.height)

    def _draw_open(self, x: int, y: int, is_ura: bool):
        if self.yellow_box is not None:
            self.yellow_box.draw(None, None, False)
            for i, song in enumerate(self.song_text):
                title, subtitle = song
                x = i * 140
                tex.draw_texture('yellow_box', 'genre_banner', x=x, frame=self.songs[i][1])
                tex.draw_texture('yellow_box', 'difficulty', x=x, frame=self.songs[i][2])
                tex.draw_texture('yellow_box', 'difficulty_x', x=x)
                tex.draw_texture('yellow_box', 'difficulty_star', x=x)
                level = self.songs[i][0].metadata.course_data[self.songs[i][2]].level
                counter = str(level)
                total_width = len(counter) * 10
                for i in range(len(counter)):
                    tex.draw_texture('yellow_box', 'difficulty_num', frame=int(counter[i]), x=x-(total_width // 2) + (i * 10))

                title.draw(outline_color=ray.BLACK, x=665+x, y=127, y2=min(title.texture.height, 400)-title.texture.height)
                subtitle.draw(outline_color=ray.BLACK, x=620+x, y=525-min(subtitle.texture.height, 400), y2=min(subtitle.texture.height, 400)-subtitle.texture.height)

            tex.draw_texture('yellow_box', 'total_notes_bg')
            tex.draw_texture('yellow_box', 'total_notes')
            counter = str(self.total_notes)
            for i in range(len(counter)):
                tex.draw_texture('yellow_box', 'total_notes_counter', frame=int(counter[i]), x=(i * 25))

            tex.draw_texture('yellow_box', 'frame', frame=self.color)
            if self.hori_name is not None:
                self.hori_name.draw(outline_color=ray.BLACK, x=434 - (self.hori_name.texture.width//2), y=84, x2=min(self.hori_name.texture.width, 275)-self.hori_name.texture.width)

            self._draw_exam_box()

    def draw(self, x: int, y: int, is_ura: bool):
        if self.is_open:
            self._draw_open(x, y, is_ura)
        else:
            self._draw_closed(x, y)

class GenreBG:
    """The background for a genre box."""
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
            self.title.draw(outline_color=ray.BLACK, x=(1280//2) - (dest_width//2)-(offset//2), y=y-60, x2=dest_width - self.title.texture.width, color=ray.fade(ray.WHITE, self.fade_in.attribute))

class ScoreHistory:
    """The score information that appears while hovering over a song"""
    def __init__(self, scores: dict[int, tuple[int, int, int, int]], current_ms):
        """
        Initialize the score history with the given scores and current time.

        Args:
            scores (dict[int, tuple[int, int, int, int]]): A dictionary of scores for each difficulty level.
            current_ms (int): The current time in milliseconds.
        """
        self.scores = {k: v for k, v in scores.items() if v is not None}
        self.difficulty_keys = list(self.scores.keys())
        self.curr_difficulty_index = 0
        self.curr_difficulty_index = (self.curr_difficulty_index + 1) % len(self.difficulty_keys)
        self.curr_difficulty = self.difficulty_keys[self.curr_difficulty_index]
        self.curr_score = self.scores[self.curr_difficulty][0]
        self.curr_score_su = self.scores[self.curr_difficulty][0]
        self.last_ms = current_ms
        self.long = True

    def update(self, current_ms):
        if current_ms >= self.last_ms + 1000:
            self.last_ms = current_ms
            self.curr_difficulty_index = (self.curr_difficulty_index + 1) % len(self.difficulty_keys)
            self.curr_difficulty = self.difficulty_keys[self.curr_difficulty_index]
            self.curr_score = self.scores[self.curr_difficulty][0]
            self.curr_score_su = self.scores[self.curr_difficulty][0]

    def draw_long(self):
        tex.draw_texture('leaderboard','background_2')
        tex.draw_texture('leaderboard','title', index=self.long)
        if self.curr_difficulty == 4:
            tex.draw_texture('leaderboard', 'shinuchi_ura', index=self.long)
        else:
            tex.draw_texture('leaderboard', 'shinuchi', index=self.long)

        tex.draw_texture('leaderboard', 'pts', color=ray.WHITE, index=self.long)
        tex.draw_texture('leaderboard', 'difficulty', frame=self.curr_difficulty, index=self.long)

        for i in range(4):
            tex.draw_texture('leaderboard', 'normal', index=self.long, y=50+(i*50))

        tex.draw_texture('leaderboard', 'judge_good')
        tex.draw_texture('leaderboard', 'judge_ok')
        tex.draw_texture('leaderboard', 'judge_bad')
        tex.draw_texture('leaderboard', 'judge_drumroll')

        for j, counter in enumerate(self.scores[self.curr_difficulty]):
            if j == 5:
                continue
            counter = str(counter)
            margin = 24
            for i in range(len(counter)):
                if j == 0:
                    tex.draw_texture('leaderboard', 'counter', frame=int(counter[i]), x=-((len(counter) * 14) // 2) + (i * 14), color=ray.WHITE, index=self.long)
                else:
                    tex.draw_texture('leaderboard', 'judge_num', frame=int(counter[i]), x=-(len(counter) - i) * margin, y=j*50)

    def draw(self):
        if self.long:
            self.draw_long()
            return
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

def parse_box_def(path: Path):
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
        logger.error(f"Error parsing box.def in {path}: {e}")

    return name, texture_index, collection

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

@dataclass
class Exam:
    type: str
    red: int
    gold: int
    range: str

class DanCourse(FileSystemItem):
    def __init__(self, path: Path, name: str):
        super().__init__(path, name)
        if name != "dan.json":
            logger.error(f"Invalid dan course file: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.title = data["title"]
            self.color = data["color"]
            self.charts = []
            for chart in data["charts"]:
                hash = chart["hash"]
                #chart_title = chart["title"]
                #chart_subtitle = chart["subtitle"]
                difficulty = chart["difficulty"]
                if hash in global_data.song_hashes:
                    path = Path(global_data.song_hashes[hash][0]["file_path"])
                    if (path.parent.parent / "box.def").exists():
                        _, genre_index, _ = parse_box_def(path.parent.parent)
                    else:
                        genre_index = 9
                    self.charts.append((TJAParser(path), genre_index, difficulty))
                else:
                    pass
                    #do something with song_title, song_subtitle
            self.exams = []
            for exam in data["exams"]:
                self.exams.append(Exam(exam["type"], exam["value"][0], exam["value"][1], exam["range"]))

        self.box = DanBox(self.title, self.color, self.charts, self.exams)

class FileNavigator:
    """Manages navigation through pre-generated Directory and SongFile objects"""
    def __init__(self):

        # Pre-generated objects storage
        self.all_directories: dict[str, Directory] = {}  # path -> Directory
        self.all_song_files: dict[str, Union[SongFile, DanCourse]] = {}    # path -> SongFile
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
        self.diff_sort_statistics = dict()
        self.history = []
        self.box_open = False
        self.genre_bg = None
        self.song_count = 0
        self.in_dan_select = False
        logger.info("FileNavigator initialized")

    def initialize(self, root_dirs: list[Path]):
        self.root_dirs = [Path(p) if not isinstance(p, Path) else p for p in root_dirs]
        self._generate_all_objects()
        self._create_virtual_root()
        self.load_current_directory()
        logger.info(f"FileNavigator initialized with root_dirs: {self.root_dirs}")

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
        logging.info("Generating all Directory and SongFile objects...")

        # Generate objects for each root directory
        for root_path in self.root_dirs:
            if not root_path.exists():
                logging.warning(f"Root directory does not exist: {root_path}")
                continue

            self._generate_objects_recursive(root_path)

        if self.favorite_folder is not None:
            song_list = self._read_song_list(self.favorite_folder.path)
            for song_obj in song_list:
                if str(song_obj) in self.all_song_files:
                    box = self.all_song_files[str(song_obj)].box
                    if isinstance(box, DanBox):
                        logger.warning(f"Cannot favorite DanCourse: {song_obj}")
                    else:
                        box.is_favorite = True

        logging.info(f"Object generation complete. "
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

            name, texture_index, collection = parse_box_def(dir_path)
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
                if song_key not in self.all_song_files and tja_path.name == "dan.json":
                    song_obj = DanCourse(tja_path, tja_path.name)
                    self.all_song_files[song_key] = song_obj
                elif song_key not in self.all_song_files and tja_path in global_data.song_paths:
                    song_obj = SongFile(tja_path, tja_path.name, texture_index)
                    song_obj.box.get_scores()
                    for course in song_obj.tja.metadata.course_data:
                        level = song_obj.tja.metadata.course_data[course].level

                        scores = song_obj.box.scores.get(course)
                        if scores is not None:
                            is_cleared = scores[4] >= 1
                            is_full_combo = (scores[4] == 2) or (scores[3] == 0)
                        else:
                            is_cleared = False
                            is_full_combo = False

                        if course not in self.diff_sort_statistics:
                            self.diff_sort_statistics[course] = {}

                        if level not in self.diff_sort_statistics[course]:
                            self.diff_sort_statistics[course][level] = [1, int(is_full_combo), int(is_cleared)]
                        else:
                            self.diff_sort_statistics[course][level][0] += 1
                            if is_full_combo:
                                self.diff_sort_statistics[course][level][1] += 1
                            elif is_cleared:
                                self.diff_sort_statistics[course][level][2] += 1
                    if song_obj.is_recent:
                        self.new_items.append(SongFile(tja_path, tja_path.name, SongBox.DEFAULT_INDEX, name_texture_index=texture_index))
                    self.song_count += 1
                    global_data.song_progress = self.song_count / global_data.total_songs
                    self.all_song_files[song_key] = song_obj

                if song_key in self.all_song_files:
                    content_items.append(self.all_song_files[song_key])

            self.directory_contents[dir_key] = content_items
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
                        logger.error(f"Error creating SongFile for {tja_path}: {e}")
                        continue

    def is_at_root(self) -> bool:
        """Check if currently at the virtual root"""
        return self.current_dir == Path()

    def load_current_directory(self, selected_item: Optional[Directory] = None):
        """Load pre-generated items for the current directory (unified for root and subdirs)"""
        dir_key = str(self.current_dir)

        # Determine if current directory has child directories with box.def
        has_children = False
        if self.is_at_root() or selected_item and selected_item.box.texture_index == 13:
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
                                    if not isinstance(item, Directory):
                                        temp_items.append(item)
                    content_items = random.sample(temp_items, 10)

            if content_items == []:
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
                hori_name = OutlinedText(diffs[min(3, self.diff_sort_diff)], 40, ray.WHITE, outline_thickness=5)
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
                logger.info(f"Entered Directory {selected_item.path}")

            self.load_current_directory(selected_item=selected_item)

        return selected_item

    def go_back(self):
        """Navigate back to the previous directory"""
        if self.history:
            previous_dir, previous_index = self.history.pop()
            self.current_dir = previous_dir
            self.selected_index = previous_index
            self.load_current_directory()
            self.box_open = False

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
                if not isinstance(song_obj, SongFile):
                    continue
                for diff in song_obj.box.scores:
                    if diff not in all_scores:
                        all_scores[diff] = []
                    all_scores[diff].append(song_obj.box.scores[diff])

        for diff in all_scores:
            if all(score is not None and ((score[5] == 2 and score[2] == 0) or (score[2] == 0 and score[3] == 0)) for score in all_scores[diff]):
                crowns[diff] = 'DFC'
            elif all(score is not None and ((score[5] == 2) or (score[3] == 0)) for score in all_scores[diff]):
                crowns[diff] = 'FC'
            elif all(score is not None and score[5] >= 1 for score in all_scores[diff]):
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
            if (path.is_file() and path.suffix.lower() == ".tja") or path.name == "dan.json":
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
                    logger.info(f"updated: {line}")
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

            # Adjust spacing based on dan select mode
            base_spacing = 100
            center_offset = 150
            side_offset_l = 0
            side_offset_r = 300

            if self.in_dan_select:
                base_spacing = 150
                side_offset_l = 200
                side_offset_r = 500

            position = BOX_CENTER + (base_spacing * offset)
            if position == BOX_CENTER:
                position += center_offset
            elif position > BOX_CENTER:
                position += side_offset_r
            else:
                position -= side_offset_l

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
            logger.info(f"Moved Left to {self.items[self.selected_index].path}")

    def navigate_right(self):
        """Move selection right with wrap-around"""
        if self.items:
            self.selected_index = (self.selected_index + 1) % len(self.items)
            self.calculate_box_positions()
            logger.info(f"Moved Right to {self.items[self.selected_index].path}")

    def get_current_item(self):
        """Get the currently selected item"""
        if self.items and 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        raise Exception("No current item available")

    def reset_items(self):
        """Reset the items in the song select scene"""
        for item in self.items:
            item.box.reset()

    def add_recent(self):
        """Add the current song to the recent list"""
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

        logger.info(f"Added Recent: {song.hash} {song.tja.metadata.title['en']} {song.tja.metadata.subtitle['en']}")

    def add_favorite(self) -> bool:
        """Add the current song to the favorites list"""
        song = self.get_current_item()
        if isinstance(song, Directory):
            return False
        if self.favorite_folder is None:
            return False
        favorites_path = self.favorite_folder.path / 'song_list.txt'
        lines = []
        if not Path(favorites_path).exists():
            Path(favorites_path).touch()
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
            logger.info(f"Removed Favorite: {song.hash} {song.tja.metadata.title['en']} {song.tja.metadata.subtitle['en']}")
        else:
            with open(favorites_path, 'a', encoding='utf-8-sig') as song_list:
                song_list.write(f'{song.hash}|{song.tja.metadata.title["en"]}|{song.tja.metadata.subtitle["en"]}\n')
            logger.info(f"Added Favorite: {song.hash} {song.tja.metadata.title['en']} {song.tja.metadata.subtitle['en']}")
        return True

navigator = FileNavigator()
