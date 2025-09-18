from pathlib import Path

import pyray as ray
from raylib import SHADER_UNIFORM_FLOAT

from libs import utils
from libs.audio import audio
from libs.chara_2d import Chara2D
from libs.global_objects import Nameplate
from libs.texture import tex
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_r_don_pressed,
    session_data,
)


class State:
    FAIL = 0
    CLEAR = 1
    RAINBOW = 2

class ResultScreen:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.screen_init = False
        self.alpha_shader = ray.load_shader('', 'shader/grayscale_alpha.fs')

    def load_textures(self):
        tex.load_screen_textures('result')

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(sounds_dir / "hit_sounds" / "0" / "don.wav")
        self.sound_kat = audio.load_sound(sounds_dir / "hit_sounds" / "0" / "ka.wav")
        self.sound_num_up = audio.load_sound(sounds_dir / "result" / "SE_RESULT [4].ogg")
        self.bgm = audio.load_sound(sounds_dir / "result" / "JINGLE_SEISEKI [1].ogg")

    def on_screen_start(self):
        if not self.screen_init:
            self.load_textures()
            self.load_sounds()
            self.screen_init = True
            self.song_info = OutlinedText(session_data.song_title, 40, ray.WHITE, ray.BLACK, outline_thickness=5)
            audio.play_sound(self.bgm)
            self.fade_in = FadeIn()
            self.fade_out = tex.get_animation(0)
            self.fade_in_bottom = tex.get_animation(1)
            self.gauge = None
            self.score_delay = None
            self.bottom_characters = BottomCharacters()
            self.crown = None
            self.state = None
            self.high_score_indicator = None
            plate_info = global_data.config['nameplate']
            self.nameplate = Nameplate(plate_info['name'], plate_info['title'], global_data.player_num, plate_info['dan'], plate_info['gold'])
            self.chara = Chara2D(global_data.player_num - 1, 100)
            self.score_animator = ScoreAnimator(session_data.result_score)
            self.score = ''
            self.good = ''
            self.ok = ''
            self.bad = ''
            self.max_combo = ''
            self.total_drumroll = ''
            self.update_list = [['score', session_data.result_score],
                ['good', session_data.result_good],
                ['ok', session_data.result_ok],
                ['bad', session_data.result_bad],
                ['max_combo', session_data.result_max_combo],
                ['total_drumroll', session_data.result_total_drumroll]]
            self.update_index = 0
            self.is_skipped = False
            self.start_ms = get_current_ms()
            if session_data.result_ok == 0 and session_data.result_bad == 0:
                self.crown_type = 'crown_dfc'
            elif session_data.result_bad == 0:
                self.crown_type = 'crown_fc'
            else:
                self.crown_type = 'crown_clear'

    def on_screen_end(self):
        self.screen_init = False
        global_data.songs_played += 1
        tex.unload_textures()
        audio.stop_sound(self.bgm)
        utils.session_data = utils.reset_session()
        return "SONG_SELECT"

    def update_score_animation(self):
        if self.is_skipped:
            if self.update_index == len(self.update_list) - 1:
                return
            setattr(self, self.update_list[self.update_index][0], self.update_list[self.update_index][1])
            self.update_index += 1
        elif self.score_delay is not None:
            if get_current_ms() > self.score_delay:
                if self.score_animator is not None and not self.score_animator.is_finished:
                    curr_num = self.update_list[self.update_index][0]
                    setattr(self, self.update_list[self.update_index][0], self.score_animator.next_score())
                    if self.update_list[self.update_index] != curr_num:
                        audio.play_sound(self.sound_num_up)
                    if self.score_animator.is_finished:
                        audio.play_sound(self.sound_don)
                        self.score_delay += 750
                        if self.update_index == len(self.update_list) - 1:
                            self.is_skipped = True
                            return
                        self.update_index += 1
                        self.score_animator = ScoreAnimator(self.update_list[self.update_index][1])
                    self.score_delay += 16.67 * 3
        if self.update_index > 0 and self.high_score_indicator is None:
            if session_data.result_score > session_data.prev_score:
                self.high_score_indicator = HighScoreIndicator(session_data.prev_score, session_data.result_score)

    def handle_input(self):
        if is_r_don_pressed() or is_l_don_pressed():
            if not self.is_skipped:
                self.is_skipped = True
            else:
                self.fade_out.start()
            audio.play_sound(self.sound_don)

    def update(self):
        self.on_screen_start()
        current_time = get_current_ms()
        self.fade_in.update(current_time)
        if self.fade_in.is_finished and self.gauge is None:
            self.gauge = Gauge(str(global_data.player_num), session_data.result_gauge_length)
            self.bottom_characters.start()

        self.bottom_characters.update(self.state)

        if self.bottom_characters.is_finished and self.crown is None:
            if self.gauge is not None and self.gauge.gauge_length > 69:
                self.crown = Crown()

        if self.gauge is not None:
            self.gauge.update(current_time)
            if self.gauge.is_finished and self.score_delay is None:
                self.score_delay = current_time + 1883

        if self.score_delay is not None:
            if current_time > self.score_delay and not self.fade_in_bottom.is_started:
                self.fade_in_bottom.start()
                if self.gauge is not None:
                    self.state = self.gauge.state

        if self.high_score_indicator is not None:
            self.high_score_indicator.update(current_time)

        self.fade_in_bottom.update(current_time)
        alpha_loc = ray.get_shader_location(self.alpha_shader, "ext_alpha")
        alpha_value = ray.ffi.new('float*', self.fade_in_bottom.attribute)
        ray.set_shader_value(self.alpha_shader, alpha_loc, alpha_value, SHADER_UNIFORM_FLOAT)

        if current_time >= self.start_ms + 5000 and not self.fade_out.is_started:
            self.handle_input()

        self.update_score_animation()

        self.fade_out.update(current_time)
        if self.fade_out.is_finished:
            self.fade_out.update(current_time)
            return self.on_screen_end()

        if self.crown is not None:
            self.crown.update(current_time)

        self.nameplate.update(current_time)
        self.chara.update(current_time, 100, False, False)

    def draw_score_info(self):
        if self.good != '':
            for i in range(len(str(self.good))):
                tex.draw_texture('score', 'judge_num', frame=int(str(self.good)[::-1][i]), x=943-(i*24), y=186)
        if self.ok != '':
            for i in range(len(str(self.ok))):
                tex.draw_texture('score', 'judge_num', frame=int(str(self.ok)[::-1][i]), x=943-(i*24), y=227)
        if self.bad != '':
            for i in range(len(str(self.bad))):
                tex.draw_texture('score', 'judge_num', frame=int(str(self.bad)[::-1][i]), x=943-(i*24), y=267)
        if self.max_combo != '':
            for i in range(len(str(self.max_combo))):
                tex.draw_texture('score', 'judge_num', frame=int(str(self.max_combo)[::-1][i]), x=1217-(i*24), y=186)
        if self.total_drumroll != '':
            for i in range(len(str(self.total_drumroll))):
                tex.draw_texture('score', 'judge_num', frame=int(str(self.total_drumroll)[::-1][i]), x=1217-(i*24), y=227)

    def draw_total_score(self):
        if not self.fade_in.is_finished:
            return
        tex.draw_texture('score', 'score_shinuchi')
        if self.score != '':
            for i in range(len(str(self.score))):
                tex.draw_texture('score', 'score_num', x=-(i*21), frame=int(str(self.score)[::-1][i]))

    def draw_bottom_textures(self):
        if self.state == State.FAIL:
            tex.draw_texture('background', 'gradient_fail', fade=min(0.4, self.fade_in_bottom.attribute))
        else:
            ray.begin_shader_mode(self.alpha_shader)
            tex.draw_texture('background', 'gradient_clear', fade=self.fade_in_bottom.attribute)
            ray.end_shader_mode()
        self.bottom_characters.draw()

    def draw_modifiers(self):
        if global_data.modifiers.display:
            tex.draw_texture('score', 'mod_doron')
        if global_data.modifiers.inverse:
            tex.draw_texture('score', 'mod_abekobe')
        if global_data.modifiers.random == 1:
            tex.draw_texture('score', 'mod_kimagure')
        elif global_data.modifiers.random == 2:
            tex.draw_texture('score', 'mod_detarame')
        if global_data.modifiers.speed >= 4:
            tex.draw_texture('score', 'mod_yonbai')
        elif global_data.modifiers.speed >= 3:
            tex.draw_texture('score', 'mod_sanbai')
        elif global_data.modifiers.speed > 1:
            tex.draw_texture('score', 'mod_baisaku')

    def draw(self):
        x = 0
        while x < self.width:
            tex.draw_texture('background', f'background_{str(global_data.player_num)}p', x=x, y=-360)
            tex.draw_texture('background', f'background_{str(global_data.player_num)}p', x=x, y=360)
            tex.draw_texture('background', f'footer_{str(global_data.player_num)}p', x=x, y=-72)
            tex.draw_texture('background', f'footer_{str(global_data.player_num)}p', x=x, y=648)
            x += 256

        tex.draw_texture('background', 'result_text')
        tex.draw_texture('song_info', 'song_num', frame=global_data.songs_played%4)
        dest = ray.Rectangle(1252 - self.song_info.texture.width, 35 - self.song_info.texture.height / 2, self.song_info.texture.width, self.song_info.texture.height)
        self.song_info.draw(self.song_info.default_src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        tex.draw_texture('score', 'overlay', color=ray.fade(ray.WHITE, 0.75))
        tex.draw_texture('score', 'difficulty', frame=session_data.selected_difficulty)

        self.draw_bottom_textures()

        if self.gauge is not None:
            self.gauge.draw()

        tex.draw_texture('score', 'judge_good')
        tex.draw_texture('score', 'judge_ok')
        tex.draw_texture('score', 'judge_bad')
        tex.draw_texture('score', 'max_combo')
        tex.draw_texture('score', 'drumroll')

        self.draw_score_info()
        self.draw_total_score()

        if self.crown is not None:
            self.crown.draw(self.crown_type)

        self.nameplate.draw(265, 80)

        self.draw_modifiers()

        if self.high_score_indicator is not None:
            self.high_score_indicator.draw()

        self.chara.draw(y=100)

        self.fade_in.draw()
        ray.draw_rectangle(0, 0, self.width, self.height, ray.fade(ray.BLACK, self.fade_out.attribute))

    def draw_3d(self):
        pass

class Crown:
    def __init__(self):
        self.resize = tex.get_animation(2)
        self.resize_fix = tex.get_animation(3)
        self.white_fadein = tex.get_animation(4)
        self.gleam = tex.get_animation(5)
        self.fadein = tex.get_animation(6)
        self.resize.start()
        self.resize_fix.start()
        self.white_fadein.start()
        self.gleam.start()
        self.fadein.start()
        self.sound = audio.load_sound(Path('Sounds/result/SE_RESULT [1].ogg'))
        self.sound_played = False

    def update(self, current_ms: float):
        self.fadein.update(current_ms)
        self.resize.update(current_ms)
        self.resize_fix.update(current_ms)
        self.white_fadein.update(current_ms)
        self.gleam.update(current_ms)
        if self.resize_fix.is_finished and not self.sound_played:
            audio.play_sound(self.sound)
            self.sound_played = True

    def draw(self, crown_name: str):
        scale = self.resize.attribute
        if self.resize.is_finished:
            scale = self.resize_fix.attribute
        tex.draw_texture('crown', crown_name, scale=scale, center=True)
        tex.draw_texture('crown', 'crown_fade', fade=self.white_fadein.attribute)
        if self.gleam.attribute >= 0:
            tex.draw_texture('crown', 'gleam', frame=self.gleam.attribute)

class BottomCharacters:
    def __init__(self):
        self.move_up = tex.get_animation(7)
        self.move_down = tex.get_animation(8)
        self.bounce_up = tex.get_animation(9)
        self.bounce_down = tex.get_animation(10)
        self.move_center = tex.get_animation(11)
        self.c_bounce_up = tex.get_animation(12)
        self.c_bounce_down = tex.get_animation(13)
        self.flower_up = tex.get_animation(14)
        self.state = None
        self.flower_index = 0
        self.flower_start = None
        self.chara_0_index = 0
        self.chara_1_index = 0
        self.is_finished = False

    def start(self):
        self.move_up.start()
        self.move_down.start()
        self.c_bounce_up.start()
        self.c_bounce_down.start()

    def update(self, state):
        self.state = state
        if self.state == State.CLEAR or self.state == State.RAINBOW:
            self.chara_0_index = 1
            self.chara_1_index = 1
            if not self.bounce_up.is_started:
                self.bounce_up.start()
                self.bounce_down.start()
                self.move_center.start()
            if self.flower_start is None:
                self.flower_up.start()
                self.flower_start = get_current_ms()
        elif self.state == State.FAIL:
            self.chara_0_index = 2
            self.chara_1_index = 2

        self.move_up.update(get_current_ms())
        self.move_down.update(get_current_ms())
        self.is_finished = self.move_down.is_finished
        self.bounce_up.update(get_current_ms())
        self.bounce_down.update(get_current_ms())
        if self.bounce_down.is_finished:
            self.bounce_up.restart()
            self.bounce_down.restart()
        self.move_center.update(get_current_ms())
        self.flower_up.update(get_current_ms())

        if self.flower_start is not None:
            if get_current_ms() > self.flower_start + 116*2 + 333:
                self.flower_index = 2
            elif get_current_ms() > self.flower_start + 116 + 333:
                self.flower_index = 1

        self.c_bounce_up.update(get_current_ms())
        self.c_bounce_down.update(get_current_ms())
        if self.c_bounce_down.is_finished:
            self.c_bounce_up.restart()
            self.c_bounce_down.restart()

    def draw_flowers(self):
        tex.draw_texture('bottom','flowers', y=-self.flower_up.attribute, frame=self.flower_index)
        tex.draw_texture('bottom','flowers', y=-self.flower_up.attribute, frame=self.flower_index, x=792, mirror='horizontal')

    def draw(self):
        self.draw_flowers()

        y = -self.move_up.attribute + self.move_down.attribute + self.bounce_up.attribute - self.bounce_down.attribute
        if self.state == State.RAINBOW:
            center_y = self.c_bounce_up.attribute - self.c_bounce_down.attribute
            tex.draw_texture('bottom', 'chara_center', y=-self.move_center.attribute + center_y)

        tex.draw_texture('bottom', 'chara_0', frame=self.chara_0_index, y=y)
        tex.draw_texture('bottom', 'chara_1', frame=self.chara_1_index, y=y)

class FadeIn:
    def __init__(self):
        self.fadein = tex.get_animation(15)
        self.fadein.start()
        self.is_finished = False

    def update(self, current_ms: float):
        self.fadein.update(current_ms)
        self.is_finished = self.fadein.is_finished

    def draw(self):
        x = 0
        while x < 1280:
            tex.draw_texture('background', f'background_{str(global_data.player_num)}p', x=x, y=-360, fade=self.fadein.attribute)
            tex.draw_texture('background', f'background_{str(global_data.player_num)}p', x=x, y=360, fade=self.fadein.attribute)
            tex.draw_texture('background', f'footer_{str(global_data.player_num)}p', x=x, y=-72, fade=self.fadein.attribute)
            tex.draw_texture('background', f'footer_{str(global_data.player_num)}p', x=x, y=648, fade=self.fadein.attribute)
            x += 256

class ScoreAnimator:
    def __init__(self, target_score):
        self.target_score = str(target_score)
        self.current_score_list = [[0,0] for _ in range(len(self.target_score))]
        self.digit_index = len(self.target_score) - 1
        self.is_finished = False

    def next_score(self) -> str:
        if self.digit_index == -1:
            self.is_finished = True
            return str(int(''.join([str(item[0]) for item in self.current_score_list])))
        curr_digit, counter = self.current_score_list[self.digit_index]
        if counter < 9:
            self.current_score_list[self.digit_index][1] += 1
            self.current_score_list[self.digit_index][0] = (curr_digit + 1) % 10
        else:
            self.current_score_list[self.digit_index][0] = int(self.target_score[self.digit_index])
            self.digit_index -= 1
        ret_val = ''.join([str(item[0]) for item in self.current_score_list])
        if int(ret_val) == 0:
            if not (len(self.target_score) - self.digit_index) > (len(self.target_score)):
                return '0' * (len(self.target_score) - self.digit_index)
            return '0'
        return str(int(ret_val))

class HighScoreIndicator:
    def __init__(self, old_score: int, new_score: int):
        self.score_diff = new_score - old_score
        self.move = tex.get_animation(18)
        self.fade = tex.get_animation(19)
        self.move.start()
        self.fade.start()

    def update(self, current_ms):
        self.move.update(current_ms)
        self.fade.update(current_ms)

    def draw(self):
        tex.draw_texture('score', 'high_score', y=self.move.attribute, fade=self.fade.attribute)
        for i in range(len(str(self.score_diff))):
            tex.draw_texture('score', 'high_score_num', x=-(i*14), frame=int(str(self.score_diff)[::-1][i]), y=self.move.attribute, fade=self.fade.attribute)


class Gauge:
    def __init__(self, player_num: str, gauge_length: int):
        self.player_num = player_num
        self.difficulty = min(2, session_data.selected_difficulty)
        self.gauge_length = gauge_length
        self.clear_start = [69, 69, 69]
        self.gauge_max = 87
        if self.difficulty >= 2:
            self.string_diff = "_hard"
        elif self.difficulty == 1:
            self.string_diff = "_normal"
        elif self.difficulty == 0:
            self.string_diff = "_easy"
        self.rainbow_animation = tex.get_animation(16)
        self.gauge_fade_in = tex.get_animation(17)
        self.rainbow_animation.start()
        self.gauge_fade_in.start()
        self.is_finished = self.gauge_fade_in.is_finished
        if self.gauge_length == self.gauge_max:
            self.state = State.RAINBOW
        elif self.gauge_length > self.clear_start[self.difficulty]:
            self.state = State.CLEAR
        else:
            self.state = State.FAIL

    def update(self, current_ms: float):
        self.rainbow_animation.update(current_ms)
        if self.rainbow_animation.is_finished:
            self.rainbow_animation.restart()
        self.gauge_fade_in.update(current_ms)
        self.is_finished = self.gauge_fade_in.is_finished

    def draw(self):
        scale = 10/11
        tex.draw_texture('gauge', f'{self.player_num}p_unfilled' + self.string_diff, scale=scale, fade=self.gauge_fade_in.attribute)
        gauge_length = int(self.gauge_length)
        if gauge_length == self.gauge_max:
            if 0 < self.rainbow_animation.attribute < 8:
                tex.draw_texture('gauge', 'rainbow'  + self.string_diff, frame=self.rainbow_animation.attribute-1, scale=scale, fade=self.gauge_fade_in.attribute)
            tex.draw_texture('gauge', 'rainbow'  + self.string_diff, frame=self.rainbow_animation.attribute, scale=scale, fade=self.gauge_fade_in.attribute)
        else:
            for i in range(gauge_length+1):
                width = int(i * 7.2)
                if i == self.clear_start[self.difficulty] - 1:
                    tex.draw_texture('gauge', 'bar_clear_transition', x=width, scale=scale, fade=self.gauge_fade_in.attribute)
                elif i > self.clear_start[self.difficulty] - 1:
                    if i % 5 == 0:
                        tex.draw_texture('gauge', 'bar_clear_top', x=width, scale=scale, fade=self.gauge_fade_in.attribute)
                        tex.draw_texture('gauge', 'bar_clear_bottom', x=width, scale=scale, fade=self.gauge_fade_in.attribute)
                    tex.draw_texture('gauge', 'bar_clear_top', x=width+1, scale=scale, fade=self.gauge_fade_in.attribute)
                    tex.draw_texture('gauge', 'bar_clear_bottom', x=width+1, scale=scale, fade=self.gauge_fade_in.attribute)
                else:
                    if i % 5 == 0:
                        tex.draw_texture('gauge', f'{self.player_num}p_bar', x=width, scale=scale, fade=self.gauge_fade_in.attribute)
                    tex.draw_texture('gauge', f'{self.player_num}p_bar', x=width+1, scale=scale, fade=self.gauge_fade_in.attribute)
        tex.draw_texture('gauge', 'overlay' + self.string_diff, scale=scale, fade=min(0.15, self.gauge_fade_in.attribute))
        tex.draw_texture('gauge', 'footer', scale=scale, fade=self.gauge_fade_in.attribute)

        if gauge_length >= self.clear_start[self.difficulty]:
            tex.draw_texture('gauge', 'clear', scale=scale, fade=self.gauge_fade_in.attribute, index=self.difficulty)
            tex.draw_texture('gauge', 'tamashii', scale=scale, fade=self.gauge_fade_in.attribute)
        else:
            tex.draw_texture('gauge', 'clear_dark', scale=scale, fade=self.gauge_fade_in.attribute)
            tex.draw_texture('gauge', 'tamashii_dark', scale=scale, fade=self.gauge_fade_in.attribute)
