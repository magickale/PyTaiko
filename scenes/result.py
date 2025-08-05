from pathlib import Path

import pyray as ray
from raylib import SHADER_UNIFORM_FLOAT

from libs import utils
from libs.animation import Animation
from libs.audio import audio
from libs.utils import (
    OutlinedText,
    draw_scaled_texture,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_r_don_pressed,
    load_all_textures_from_zip,
    session_data,
)


class State:
    FAIL = 0
    CLEAR = 1
    RAINBOW = 2

class ResultScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.screen_init = False
        self.alpha_shader = ray.load_shader('', 'shader/grayscale_alpha.fs')

    def load_textures(self):
        zip_file = Path('Graphics/lumendata/enso_result.zip')
        self.textures = load_all_textures_from_zip(zip_file)

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(sounds_dir / "inst_00_don.wav")
        self.sound_kat = audio.load_sound(sounds_dir / "inst_00_katsu.wav")
        self.sound_num_up = audio.load_sound(sounds_dir / "result" / "SE_RESULT [4].ogg")
        self.bgm = audio.load_sound(sounds_dir / "result" / "JINGLE_SEISEKI [1].ogg")

    def on_screen_start(self):
        if not self.screen_init:
            self.load_textures()
            self.load_sounds()
            self.screen_init = True
            self.song_info = OutlinedText(session_data.song_title, 40, ray.Color(255, 255, 255, 255), ray.Color(0, 0, 0, 255), outline_thickness=5)
            audio.play_sound(self.bgm)
            self.fade_in = FadeIn()
            self.fade_out = None
            self.fade_in_bottom = None
            self.gauge = None
            self.score_delay = None
            self.bottom_characters = BottomCharacters()
            self.crown = None
            self.state = None
            self.score_animator = ScoreAnimator(session_data.result_score)
            self.score = -1
            self.good = -1
            self.ok = -1
            self.bad = -1
            self.max_combo = -1
            self.total_drumroll = -1
            self.update_list = [['score', session_data.result_score],
                ['good', session_data.result_good],
                ['ok', session_data.result_ok],
                ['bad', session_data.result_bad],
                ['total_drumroll', session_data.result_total_drumroll],
                ['max_combo', session_data.result_max_combo]]
            self.update_index = 0
            self.is_skipped = False
            self.start_ms = get_current_ms()
            if session_data.result_bad == 0:
                self.crown_texture = 125
            else:
                self.crown_texture = 124

    def on_screen_end(self):
        self.screen_init = False
        global_data.songs_played += 1
        for zip in self.textures:
            for texture in self.textures[zip]:
                ray.unload_texture(texture)
        audio.stop_sound(self.bgm)
        utils.session_data = utils.reset_session()
        return "SONG_SELECT"

    def update_score_animation(self, is_skipped):
        if self.is_skipped:
            setattr(self, self.update_list[self.update_index][0], self.update_list[self.update_index][1])
            if self.update_index == len(self.update_list) - 1:
                return
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

    def handle_input(self):
        if is_r_don_pressed() or is_l_don_pressed():
            if not self.is_skipped:
                self.is_skipped = True
            else:
                if self.fade_out is None:
                    self.fade_out = FadeOut()
            audio.play_sound(self.sound_don)

    def update(self):
        self.on_screen_start()

        if self.fade_in is not None:
            self.fade_in.update(get_current_ms())
            if self.fade_in.is_finished and self.gauge is None:
                self.gauge = Gauge(get_current_ms(), session_data.result_gauge_length)
                self.bottom_characters.start()

        self.bottom_characters.update(self.state)

        if self.bottom_characters.is_finished and self.crown is None:
            if self.gauge is not None and self.gauge.gauge_length > 69:
                self.crown = Crown()

        if self.gauge is not None:
            self.gauge.update(get_current_ms())
            if self.gauge.is_finished and self.score_delay is None:
                self.score_delay = get_current_ms() + 1883

        if self.score_delay is not None:
            if get_current_ms() > self.score_delay and self.fade_in_bottom is None:
                self.fade_in_bottom = Animation.create_fade(333, initial_opacity=0.0, final_opacity=1.0)
                self.fade_in_bottom.start()
                if self.gauge is not None:
                    self.state = self.gauge.state


        if self.fade_in_bottom is not None:
            self.fade_in_bottom.update(get_current_ms())
            alpha_loc = ray.get_shader_location(self.alpha_shader, "ext_alpha")
            alpha_value = ray.ffi.new('float*', self.fade_in_bottom.attribute)
            ray.set_shader_value(self.alpha_shader, alpha_loc, alpha_value, SHADER_UNIFORM_FLOAT)

        if get_current_ms() >= self.start_ms + 5000:
            self.handle_input()

        self.update_score_animation(self.is_skipped)

        if self.fade_out is not None:
            self.fade_out.update(get_current_ms())
            if self.fade_out.is_finished:
                return self.on_screen_end()

        if self.crown is not None:
            self.crown.update(get_current_ms())

    def draw_score_info(self):
        if self.good > -1:
            for i in range(len(str(self.good))):
                ray.draw_texture(self.textures['result'][int(str(self.good)[::-1][i]) + 136], 943-(i*24), 186, ray.WHITE)
        if self.ok > -1:
            for i in range(len(str(self.ok))):
                ray.draw_texture(self.textures['result'][int(str(self.ok)[::-1][i]) + 136], 943-(i*24), 227, ray.WHITE)
        if self.bad > -1:
            for i in range(len(str(self.bad))):
                ray.draw_texture(self.textures['result'][int(str(self.bad)[::-1][i]) + 136], 943-(i*24), 267, ray.WHITE)
        if self.max_combo > -1:
            for i in range(len(str(self.max_combo))):
                ray.draw_texture(self.textures['result'][int(str(self.max_combo)[::-1][i]) + 136], 1217-(i*24), 227, ray.WHITE)
        if self.total_drumroll > -1:
            for i in range(len(str(self.total_drumroll))):
                ray.draw_texture(self.textures['result'][int(str(self.total_drumroll)[::-1][i]) + 136], 1217-(i*24), 186, ray.WHITE)

    def draw_total_score(self):
        if self.fade_in is None:
            return

        if not self.fade_in.is_finished:
            return
        ray.draw_texture(self.textures['result'][167], 554, 236, ray.WHITE)
        if self.score > -1:
            for i in range(len(str(self.score))):
                ray.draw_texture(self.textures['result'][int(str(self.score)[::-1][i]) + 156], 723-(i*21), 252, ray.WHITE)

    def draw_bottom_textures(self):
        if self.fade_in_bottom is not None:
            src = ray.Rectangle(0, 0, self.textures['result'][328].width, self.textures['result'][328].height)
            if self.state == State.FAIL:
                dest = ray.Rectangle(0, self.height//2, self.width, self.height//2)
                ray.draw_texture_pro(self.textures['result'][329], src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, min(0.4, self.fade_in_bottom.attribute)))
            else:
                dest = ray.Rectangle(0, self.height//2 - 72, self.width, self.height//2)
                ray.begin_shader_mode(self.alpha_shader)
                ray.draw_texture_pro(self.textures['result'][328], src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, self.fade_in_bottom.attribute))
                ray.end_shader_mode()
        self.bottom_characters.draw(self.textures['result'])

    def draw(self):
        x = 0
        while x < self.width:
            ray.draw_texture(self.textures['result'][326], x, 0 - self.textures['result'][326].height//2, ray.WHITE)
            ray.draw_texture(self.textures['result'][326], x, self.height - self.textures['result'][326].height//2, ray.WHITE)
            x += self.textures['result'][326].width
        x = 0
        while x < self.width:
            ray.draw_texture(self.textures['result'][327], x, 0 - self.textures['result'][327].height//2, ray.WHITE)
            ray.draw_texture(self.textures['result'][327], x, self.height - self.textures['result'][327].height + self.textures['result'][327].height//2, ray.WHITE)
            x += self.textures['result'][327].width

        ray.draw_texture(self.textures['result'][330], -5, 3, ray.WHITE)
        ray.draw_texture(self.textures['result'][(global_data.songs_played % 4) + 331], 232, 4, ray.WHITE)
        src = ray.Rectangle(0, 0, self.song_info.texture.width, self.song_info.texture.height)
        dest = ray.Rectangle(1252 - self.song_info.texture.width, 35 - self.song_info.texture.height / 2, self.song_info.texture.width, self.song_info.texture.height)
        self.song_info.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        ray.draw_texture(self.textures['result'][175], 532, 98, ray.fade(ray.WHITE, 0.75))

        ray.draw_texture(self.textures['result'][233 + session_data.selected_difficulty], 289, 129, ray.WHITE)

        self.draw_bottom_textures()

        if self.gauge is not None:
            self.gauge.draw(self.textures['result'])

        ray.draw_texture(self.textures['result'][170], 817, 186, ray.WHITE)
        ray.draw_texture(self.textures['result'][171], 817, 227, ray.WHITE)
        ray.draw_texture(self.textures['result'][172], 817, 267, ray.WHITE)
        ray.draw_texture(self.textures['result'][173], 987, 186, ray.WHITE)
        ray.draw_texture(self.textures['result'][174], 981, 227, ray.WHITE)

        self.draw_score_info()
        self.draw_total_score()

        if self.crown is not None:
            self.crown.draw(self.textures['result'], self.crown_texture)

        if self.fade_in is not None:
            self.fade_in.draw(self.width, self.height, self.textures['result'][326], self.textures['result'][327])

        if self.fade_out is not None:
            self.fade_out.draw(self.width, self.height)

    def draw_3d(self):
        pass

class Crown:
    def __init__(self):
        duration = 466
        self.resize = Animation.create_texture_resize(duration, initial_size=3.5, final_size=0.90, ease_in='quadratic')
        self.resize.start()
        self.resize_fix = Animation.create_texture_resize(216, initial_size=self.resize.final_size, final_size=1.0, delay=self.resize.duration)
        self.resize_fix.start()
        self.white_fadein = Animation.create_fade(133, initial_opacity=0.0, final_opacity=1.0, delay=self.resize.duration + self.resize_fix.duration, reverse_delay=0)
        self.white_fadein.start()
        self.gleam = Animation.create_texture_change(400, textures=[(0, 200, 0), (200, 250, 127), (250, 300, 128), (300, 350, 129), (350, 400, 0)], delay=self.resize.duration + self.resize_fix.duration + self.white_fadein.duration)
        self.gleam.start()
        self.fadein = Animation.create_fade(duration, initial_opacity=0.0, final_opacity=1.0, ease_in='quadratic')
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

    def draw(self, textures: list[ray.Texture], crown_index: int):
        scale = self.resize.attribute
        if self.resize.is_finished:
            scale = self.resize_fix.attribute
        texture = textures[crown_index]
        x_x = 335 + (texture.width//2) - ((texture.width * scale)//2)
        x_y = 150 + (texture.height//2) - ((texture.height * scale)//2)
        x_source = ray.Rectangle(0, 0, texture.width, texture.height)
        x_dest = ray.Rectangle(x_x, x_y, texture.width*scale, texture.height*scale)
        ray.draw_texture_pro(texture, x_source, x_dest, ray.Vector2(0,0), 0, ray.fade(ray.WHITE, self.fadein.attribute))
        ray.draw_texture(textures[126], int(x_x), int(x_y), ray.fade(ray.WHITE, self.white_fadein.attribute))
        if self.gleam.attribute != 0:
            ray.draw_texture(textures[self.gleam.attribute], int(x_x), int(x_y), ray.WHITE)

class BottomCharacters:
    def __init__(self):
        self.move_up = None
        self.move_down = None
        self.move_center = None
        self.bounce_up = None
        self.bounce_down = None
        self.flower_up = None
        self.state = None
        self.flower_index = 341
        self.flower_start = None
        self.char_1_index = 339
        self.char_2_index = 340
        self.c_bounce_up = Animation.create_move(266, total_distance=40, ease_in='quadratic')
        self.c_bounce_up.start()
        self.c_bounce_down = Animation.create_move(266, total_distance=40, ease_out='quadratic', delay=self.c_bounce_up.duration)
        self.c_bounce_down.start()
        self.is_finished = False

    def start(self):
        self.move_up = Animation.create_move(366, total_distance=380, ease_out='cubic')
        self.move_up.start()
        self.move_down = Animation.create_move(133, total_distance=30, ease_out='cubic', delay=self.move_up.duration-5)
        self.move_down.start()

    def update(self, state):
        self.state = state
        if self.state == State.CLEAR or self.state == State.RAINBOW:
            self.char_1_index = 345
            self.char_2_index = 346
            if self.bounce_up is None:
                self.bounce_up = Animation.create_move(266, total_distance=40, ease_in='quadratic')
                self.bounce_up.start()
                self.bounce_down = Animation.create_move(266, total_distance=40, ease_out='quadratic', delay=self.bounce_up.duration)
                self.bounce_down.start()
                self.move_center = Animation.create_move(266, total_distance=450, ease_out='quadratic', delay=self.bounce_down.duration+self.bounce_up.duration)
                self.move_center.start()
            if self.flower_up is None:
                self.flower_up = Animation.create_move(333, total_distance=365, ease_out='quadratic')
                self.flower_up.start()
                self.flower_start = get_current_ms()
        elif self.state == State.FAIL:
            self.char_1_index = 347
            self.char_2_index = 348

        if self.move_up is not None:
            self.move_up.update(get_current_ms())
        if self.move_down is not None:
            self.move_down.update(get_current_ms())
            self.is_finished = self.move_down.is_finished
        if self.bounce_up is not None:
            self.bounce_up.update(get_current_ms())
        if self.bounce_down is not None:
            self.bounce_down.update(get_current_ms())
            if self.bounce_down.is_finished and self.bounce_up is not None:
                self.bounce_up.restart()
                self.bounce_down.restart()
        if self.move_center is not None:
            self.move_center.update(get_current_ms())
        if self.flower_up is not None:
            self.flower_up.update(get_current_ms())

        if self.flower_start is not None:
            if get_current_ms() > self.flower_start + 116*2 + 333:
                self.flower_index = 343
            elif get_current_ms() > self.flower_start + 116 + 333:
                self.flower_index = 342

        self.c_bounce_up.update(get_current_ms())
        self.c_bounce_down.update(get_current_ms())
        if self.c_bounce_down.is_finished:
            self.c_bounce_up.restart()
            self.c_bounce_down.restart()

    def draw_flowers(self, textures: list[ray.Texture]):
        if self.flower_up is None:
            return
        y = 720+textures[self.flower_index].height - int(self.flower_up.attribute)
        source_rect = ray.Rectangle(0, 0, textures[self.flower_index].width, textures[self.flower_index].height)
        dest_rect = ray.Rectangle(1280-textures[self.flower_index].width, y, textures[self.flower_index].width, textures[self.flower_index].height)
        source_rect.width = -textures[self.flower_index].width
        ray.draw_texture_pro(textures[self.flower_index], source_rect, dest_rect, ray.Vector2(0, 0), 0, ray.WHITE)
        ray.draw_texture(textures[self.flower_index], 0, y, ray.WHITE)

    def draw(self, textures: list[ray.Texture]):
        if self.move_up is None or self.move_down is None:
            return

        self.draw_flowers(textures)

        y = 720 - int(self.move_up.attribute) + int(self.move_down.attribute)
        if self.bounce_up is not None and self.bounce_down is not None:
            y = 720 - int(self.move_up.attribute) + int(self.move_down.attribute) + int(self.bounce_up.attribute) - int(self.bounce_down.attribute)
            if self.state == State.RAINBOW and self.move_center is not None:
                center_y = int(self.c_bounce_up.attribute) - int(self.c_bounce_down.attribute)
                ray.draw_texture(textures[344], 1280//2 - textures[344].width//2, (800 - int(self.move_center.attribute)) + int(center_y), ray.WHITE)

        ray.draw_texture(textures[self.char_1_index], 125, y, ray.WHITE)
        ray.draw_texture(textures[self.char_2_index], 820, y, ray.WHITE)

class FadeIn:
    def __init__(self):
        self.fadein = Animation.create_fade(450, initial_opacity=1.0, final_opacity=0.0, delay=100)
        self.fadein.start()
        self.fade = ray.fade(ray.WHITE, self.fadein.attribute)

        self.is_finished = False

    def update(self, current_ms: float):
        self.fadein.update(current_ms)
        self.fade = ray.fade(ray.WHITE, self.fadein.attribute)
        self.is_finished = self.fadein.is_finished

    def draw(self, screen_width: int, screen_height: int, texture_1: ray.Texture, texture_2: ray.Texture):
        x = 0
        while x < screen_width:
            ray.draw_texture(texture_1, x, 0 - texture_1.height//2, self.fade)
            ray.draw_texture(texture_1, x, screen_height - texture_1.height//2, self.fade)
            x += texture_1.width
        x = 0
        while x < screen_width:
            ray.draw_texture(texture_2, x, 0 - texture_2.height//2, self.fade)
            ray.draw_texture(texture_2, x, screen_height - texture_2.height + texture_2.height//2, self.fade)
            x += texture_2.width

class ScoreAnimator:
    def __init__(self, target_score):
        self.target_score = str(target_score)
        self.current_score_list = [[0,0] for i in range(len(self.target_score))]
        self.digit_index = len(self.target_score) - 1
        self.is_finished = False

    def next_score(self):
        if self.digit_index == -1:
            self.is_finished = True
            return int(''.join([str(item[0]) for item in self.current_score_list]))
        curr_digit, counter = self.current_score_list[self.digit_index]
        if counter < 9:
            self.current_score_list[self.digit_index][1] += 1
            self.current_score_list[self.digit_index][0] = (curr_digit + 1) % 10
        else:
            self.current_score_list[self.digit_index][0] = int(self.target_score[self.digit_index])
            self.digit_index -= 1
        return int(''.join([str(item[0]) for item in self.current_score_list]))

class Gauge:
    def __init__(self, current_ms: float, gauge_length):
        self.gauge_length = gauge_length
        self.rainbow_animation = None
        self.gauge_fade_in = Animation.create_fade(366, initial_opacity=0.0, final_opacity=1.0)
        self.gauge_fade_in.start()
        self.is_finished = self.gauge_fade_in.is_finished
        if self.gauge_length == 87:
            self.state = State.RAINBOW
        elif self.gauge_length > 69:
            self.state = State.CLEAR
        else:
            self.state = State.FAIL

    def _create_rainbow_anim(self, current_ms):
        anim = Animation.create_texture_change((16.67*8) * 3, textures=[((16.67 * 3) * i, (16.67 * 3) * (i + 1), i) for i in range(8)])
        anim.start()
        return anim

    def _create_anim(self, current_ms: float, init: float, final: float):
        anim = Animation.create_fade(450, initial_opacity=init, final_opacity=final)
        anim.start()
        return anim

    def update(self, current_ms: float):
        if self.rainbow_animation is None:
            self.rainbow_animation = self._create_rainbow_anim(current_ms)
        else:
            self.rainbow_animation.update(current_ms)
            if self.rainbow_animation.is_finished:
                self.rainbow_animation = None
        self.gauge_fade_in.update(current_ms)
        self.is_finished = self.gauge_fade_in.is_finished

    def draw(self, textures: list[ray.Texture]):
        color = ray.fade(ray.WHITE, self.gauge_fade_in.attribute)
        draw_scaled_texture(textures[217], 554, 109, (10/11), color)
        gauge_length = int(self.gauge_length)
        if gauge_length == 87 and self.rainbow_animation is not None:
            if 0 < self.rainbow_animation.attribute < 8:
                draw_scaled_texture(textures[217 + int(self.rainbow_animation.attribute)], 554, 109, (10/11), color)
            draw_scaled_texture(textures[218 + int(self.rainbow_animation.attribute)], 554, 109, (10/11), color)
        else:
            for i in range(gauge_length+1):
                width = int(i * 7.2)
                if i == 69:
                    draw_scaled_texture(textures[192], 562 + width, 142 - 22, (10/11), color)
                elif i > 69:
                    if i % 5 == 0:
                        draw_scaled_texture(textures[191], 561 + width, 142 - 20, (10/11), color)
                        draw_scaled_texture(textures[196], 561 + width, 142, (10/11), color)
                    draw_scaled_texture(textures[191], 562 + width, 142 - 20, (10/11), color)
                    draw_scaled_texture(textures[196], 562 + width, 142, (10/11), color)
                else:
                    if i % 5 == 0:
                        draw_scaled_texture(textures[189], 561 + width, 142, (10/11), color)
                    draw_scaled_texture(textures[189], 562 + width, 142, (10/11), color)
        draw_scaled_texture(textures[226], 554, 109, (10/11), ray.fade(ray.WHITE, min(0.15, self.gauge_fade_in.attribute)))
        draw_scaled_texture(textures[176], 1185, 116, (10/11), color)

        if gauge_length >= 69:
            draw_scaled_texture(textures[194], 1058, 124, (10/11), color)
            draw_scaled_texture(textures[195], 1182, 115, (10/11), color)
        else:
            draw_scaled_texture(textures[187], 1058, 124, (10/11), color)
            draw_scaled_texture(textures[188], 1182, 115, (10/11), color)

class FadeOut:
    def __init__(self) -> None:
        self.texture = global_data.textures['scene_change_fade'][0]
        self.fade_out = Animation.create_fade(1000, initial_opacity=0.0, final_opacity=1.0)
        self.fade_out.start()
        self.is_finished = False
    def update(self, current_time_ms: float):
        self.fade_out.update(current_time_ms)
        self.is_finished = self.fade_out.is_finished
    def draw(self, screen_width: int, screen_height: int):
        src = ray.Rectangle(0, 0, self.texture.width, self.texture.height)
        dst = ray.Rectangle(0, 0, screen_width, screen_height)
        ray.draw_texture_pro(self.texture, src, dst, ray.Vector2(0,0), 0, ray.fade(ray.WHITE, self.fade_out.attribute))
