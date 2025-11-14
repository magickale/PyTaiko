import logging
import pyray as ray

from libs.animation import Animation
from libs.chara_2d import Chara2D
from libs.global_data import PlayerNum, reset_session
from libs.audio import audio
from libs.global_objects import AllNetIcon, CoinOverlay, Nameplate
from libs.screen import Screen
from libs.texture import tex
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_r_don_pressed
)
from scenes.game import Gauge
from scenes.result import Background

logger = logging.getLogger(__name__)

class DanResultScreen(Screen):
    def on_screen_start(self):
        super().on_screen_start()
        audio.play_sound('bgm', 'music')
        self.fade_out = tex.get_animation(0)
        self.coin_overlay = CoinOverlay()
        self.allnet_indicator = AllNetIcon()
        self.start_ms = get_current_ms()
        self.background = Background(PlayerNum.DAN, 1280)
        self.player = DanResultPlayer(global_data.player_num)
        self.is_result_2 = False
        self.result_2_fade_in = tex.get_animation(1)
        self.gauge = DanGauge(global_data.player_num, global_data.session_data[global_data.player_num].dan_result_data.gauge_length)
        self.song_names = [OutlinedText(song.song_title, 40, ray.WHITE) for song in global_data.session_data[global_data.player_num].dan_result_data.songs]
        self.hori_name = OutlinedText(global_data.session_data[global_data.player_num].dan_result_data.dan_title, 40, ray.WHITE)
        self.exam_info = global_data.session_data[global_data.player_num].dan_result_data.exams
        self.exam_data = global_data.session_data[global_data.player_num].dan_result_data.exam_data
        print(global_data.session_data[global_data.player_num].dan_result_data.songs)

    def on_screen_end(self, next_screen: str):
        reset_session()
        return super().on_screen_end(next_screen)

    def handle_input(self):
        if is_r_don_pressed() or is_l_don_pressed():
            if self.is_result_2:
                self.fade_out.start()
                audio.play_sound('don', 'sound')
            else:
                audio.play_sound('don', 'sound')
                self.result_2_fade_in.start()
                self.is_result_2 = True

    def update(self):
        super().update()
        current_time = get_current_ms()
        self.player.update(current_time)
        self.handle_input()

        self.result_2_fade_in.update(current_time)
        self.fade_out.update(current_time)
        self.gauge.update(current_time)
        if self.fade_out.is_finished:
            self.fade_out.update(current_time)
            return self.on_screen_end("DAN_SELECT")

    def draw_overlay(self):
        ray.draw_rectangle(0, 0, 1280, 720, ray.fade(ray.BLACK, self.fade_out.attribute))
        self.coin_overlay.draw()
        self.allnet_indicator.draw()

    def draw_song_info_1(self):
        result_data = global_data.session_data[global_data.player_num].dan_result_data
        height = 191
        for i in range(len(result_data.songs)):
            song = result_data.songs[i]
            tex.draw_texture('background', 'genre_banner', y=i*height, frame=song.genre_index)
            self.song_names[i].draw(x=1230 - self.song_names[i].texture.width, y=i*height + 90)
            tex.draw_texture('result_info', 'song_num', frame=i, y=i*height)
            tex.draw_texture('result_info', 'difficulty', frame=song.selected_difficulty, y=i*height)

            tex.draw_texture('result_info', 'diff_star', y=i*height)
            tex.draw_texture('result_info', 'diff_x', y=i*height)
            counter = str(song.diff_level)[::-1]
            margin = 12
            for j, digit in enumerate(counter):
                tex.draw_texture('result_info', 'diff_num', frame=int(digit), x=-(j*margin), y=i*height)

            tex.draw_texture('result_info', 'good', y=i*height)
            margin = 24
            counter = str(song.good)[::-1]
            for j, digit in enumerate(counter):
                tex.draw_texture('result_info', 'counter', index=0, frame=int(digit), x=-(j*margin), y=i*height)
            tex.draw_texture('result_info', 'ok', y=i*height)
            counter = str(song.ok)[::-1]
            for j, digit in enumerate(counter):
                tex.draw_texture('result_info', 'counter', index=1, frame=int(digit), x=-(j*margin), y=i*height)
            tex.draw_texture('result_info', 'bad', y=i*height)
            counter = str(song.bad)[::-1]
            for j, digit in enumerate(counter):
                tex.draw_texture('result_info', 'counter', index=2, frame=int(digit), x=-(j*margin), y=i*height)
            tex.draw_texture('result_info', 'drumroll', y=i*height)
            counter = str(song.drumroll)[::-1]
            for j, digit in enumerate(counter):
                tex.draw_texture('result_info', 'counter', index=3, frame=int(digit), x=-(j*margin), y=i*height)

    def draw_song_info_2(self, fade: float):
        result_data = global_data.session_data[global_data.player_num].dan_result_data
        tex.draw_texture('background', 'result_2_bg', fade=fade)
        for i in range(5):
            tex.draw_texture('background', 'result_2_divider', fade=fade, x=i*240)
        tex.draw_texture('background', 'result_2_pullout', fade=fade)
        tex.draw_texture('result_info', 'dan_emblem', fade=fade, frame=result_data.dan_color)
        self.hori_name.draw(outline_color=ray.BLACK, x=276 - (self.hori_name.texture.width//2),
                           y=123, x2=min(self.hori_name.texture.width, 275)-self.hori_name.texture.width, color=ray.fade(ray.WHITE, fade))

        tex.draw_texture('result_info', 'good', index=1, fade=fade)
        margin = 24
        counter = str(sum(song.good for song in result_data.songs))[::-1]
        for j, digit in enumerate(counter):
            tex.draw_texture('result_info', 'counter', index=4, frame=int(digit), x=-(j*margin), fade=fade)
        tex.draw_texture('result_info', 'ok', index=1, fade=fade)
        counter = str(sum(song.ok for song in result_data.songs))[::-1]
        for j, digit in enumerate(counter):
            tex.draw_texture('result_info', 'counter', index=5, frame=int(digit), x=-(j*margin), fade=fade)
        tex.draw_texture('result_info', 'bad', index=1, fade=fade)
        counter = str(sum(song.bad for song in result_data.songs))[::-1]
        for j, digit in enumerate(counter):
            tex.draw_texture('result_info', 'counter', index=6, frame=int(digit), x=-(j*margin), fade=fade)
        tex.draw_texture('result_info', 'drumroll', index=1, fade=fade)
        counter = str(sum(song.drumroll for song in result_data.songs))[::-1]
        for j, digit in enumerate(counter):
            tex.draw_texture('result_info', 'counter', index=7, frame=int(digit), x=-(j*margin), fade=fade)
        tex.draw_texture('result_info', 'max_combo', fade=fade)
        counter = str(result_data.max_combo)[::-1]
        for j, digit in enumerate(counter):
            tex.draw_texture('result_info', 'counter', index=8, frame=int(digit), x=-(j*margin), fade=fade)
        tex.draw_texture('result_info', 'max_hits', fade=fade)
        counter = str(sum(song.drumroll + song.ok + song.bad + song.good for song in result_data.songs))[::-1]
        for j, digit in enumerate(counter):
            tex.draw_texture('result_info', 'counter', index=9, frame=int(digit), x=-(j*margin), fade=fade)
        tex.draw_texture('result_info', 'exam_header', fade=fade)

        tex.draw_texture('result_info', 'score_box', fade=fade)
        margin = 22
        counter = str(result_data.score)[::-1]
        for j, digit in enumerate(counter):
            tex.draw_texture('result_info', 'score_counter', frame=int(digit), x=-(j*margin), fade=fade)

        self.gauge.draw(fade)

        self.draw_dan_info(fade)

        if any(exam_data.failed for exam_data in self.exam_data):
            tex.draw_texture('exam_info', 'fail', fade=fade)
        elif all(exam_data.progress >= exam.gold for exam_data, exam in zip(self.exam_data, self.exam_info)):
            tex.draw_texture('exam_info', 'gold_clear', fade=fade)
        else:
            tex.draw_texture('exam_info', 'red_clear', fade=fade)

    def draw_dan_info(self, fade: float, scale=0.8):
        # Draw exam info
        for i, exam in enumerate(self.exam_info):
            exam_data = self.exam_data[i]
            y_offset = i * 94 * scale  # Scale the y offset
            tex.draw_texture('exam_info', 'exam_bg', y=y_offset, fade=fade, scale=scale)
            tex.draw_texture('exam_info', 'exam_overlay_1', y=y_offset, fade=fade, scale=scale)
            # Draw progress bar
            tex.draw_texture('exam_info', exam_data.bar_texture, x2=940*exam_data.progress*scale, y=y_offset, fade=fade, scale=scale)
            # Draw exam type and red value counter
            red_counter = str(exam.red)
            self._draw_counter(red_counter, margin=22*scale, texture='value_counter', index=0, y=y_offset, fade=fade, scale=scale)
            tex.draw_texture('exam_info', f'exam_{exam.type}', y=y_offset, x=-len(red_counter)*20*scale, fade=fade, scale=scale)
            # Draw range indicator
            if exam.range == 'less':
                tex.draw_texture('exam_info', 'exam_less', y=y_offset, fade=fade, scale=scale)
            elif exam.range == 'more':
                tex.draw_texture('exam_info', 'exam_more', y=y_offset, fade=fade, scale=scale)
            # Draw current value counter
            tex.draw_texture('exam_info', 'exam_overlay_2', y=y_offset, fade=fade, scale=scale)
            value_counter = str(exam_data.counter_value)
            self._draw_counter(value_counter, margin=22*scale, texture='value_counter', index=1, y=y_offset, fade=fade, scale=scale)
            if exam.type == 'gauge':
                tex.draw_texture('exam_info', 'exam_percent', y=y_offset, index=1, fade=fade, scale=scale)
            if exam_data.failed:
                tex.draw_texture('exam_info', 'exam_bg', fade=min(fade, 0.5), y=y_offset, scale=scale)
                tex.draw_texture('exam_info', 'exam_failed', y=y_offset, fade=fade, scale=scale)

    def _draw_counter(self, counter, margin, texture, index=None, y: float = 0.0, fade=0.0, scale=1.0):
        """Helper to draw digit counters"""
        for j in range(len(counter)):
            kwargs = {'frame': int(counter[j]), 'x': -(len(counter) - j) * margin, 'y': y, 'fade': fade, 'scale': scale}
            if index is not None:
                kwargs['index'] = index
            tex.draw_texture('exam_info', texture, **kwargs)

    def draw(self):
        self.background.draw()
        self.draw_song_info_1()
        self.draw_song_info_2(self.result_2_fade_in.attribute)
        self.player.draw()
        self.draw_overlay()

class DanResultPlayer:
    def __init__(self, player_num: PlayerNum):
        plate_info = global_data.config[f'nameplate_{player_num}p']
        self.nameplate = Nameplate(plate_info['name'], plate_info['title'], player_num, plate_info['dan'], plate_info['gold'], plate_info['rainbow'], plate_info['title_bg'])
        self.chara = Chara2D(player_num-1, 100)

    def update(self, current_time_ms: float):
        self.nameplate.update(current_time_ms)
        self.chara.update(current_time_ms, 100, False, False)

    def draw(self):
        self.nameplate.draw(10, 585)
        self.chara.draw(0, 405)

class DanGauge(Gauge):
    """The player's gauge"""
    def __init__(self, player_num: PlayerNum, gauge_length: float):
        self.player_num = player_num
        self.gauge_length = gauge_length
        self.visual_length = int(self.gauge_length * 8)
        self.gauge_max = 89
        self.tamashii_fire_change = tex.get_animation(25)
        self.is_clear = False
        self.is_rainbow = False
        self.rainbow_animation = Animation.create_texture_change((16.67*8) * 3, textures=[((16.67 * 3) * i, (16.67 * 3) * (i + 1), i) for i in range(8)])
        self.rainbow_animation.start()
        self.rainbow_fade_in = Animation.create_fade(450, initial_opacity=0.0, final_opacity=1.0)
        self.rainbow_fade_in.start()

    def update(self, current_ms: float):
        self.is_rainbow = self.gauge_length == self.gauge_max
        self.is_clear = self.is_rainbow
        self.tamashii_fire_change.update(current_ms)
        self.rainbow_animation.update(current_ms)
        self.rainbow_fade_in.update(current_ms)
        if self.rainbow_animation.is_finished:
            self.rainbow_animation.restart()

    def draw(self, fade: float = 1.0):
        tex.draw_texture('gauge', f'{self.player_num}p_unfilled', fade=fade)

        if not self.is_rainbow:
            tex.draw_texture('gauge', f'{self.player_num}p_bar', x2=self.visual_length-8, fade=fade)

        # Rainbow effect for full gauge
        if self.is_rainbow:
            if 0 < self.rainbow_animation.attribute < 8:
                tex.draw_texture('gauge', 'rainbow', frame=self.rainbow_animation.attribute-1, fade=min(self.rainbow_fade_in.attribute, fade))
            tex.draw_texture('gauge', 'rainbow', frame=self.rainbow_animation.attribute, fade=min(self.rainbow_fade_in.attribute, fade))
        tex.draw_texture('gauge', 'overlay', fade=min(fade, 0.15))

        # Draw clear status indicators
        tex.draw_texture('gauge', 'footer', fade=fade)
        if self.is_rainbow:
            tex.draw_texture('gauge', 'tamashii_fire', scale=0.75, center=True, frame=self.tamashii_fire_change.attribute, fade=fade)
            tex.draw_texture('gauge', 'tamashii', fade=fade)
            if self.is_rainbow and self.tamashii_fire_change.attribute in (0, 1, 4, 5):
                tex.draw_texture('gauge', 'tamashii_overlay', fade=min(fade, 0.5))
        else:
            tex.draw_texture('gauge', 'tamashii_dark', fade=fade)
