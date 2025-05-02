from pathlib import Path

import pyray as ray

from libs import utils
from libs.animation import Animation
from libs.audio import audio
from libs.utils import (
    OutlinedText,
    draw_scaled_texture,
    get_config,
    get_current_ms,
    global_data,
    load_all_textures_from_zip,
    session_data,
)


class ResultScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.screen_init = False
        self.load_sounds()

    def load_textures(self):
        zip_file = Path('Graphics/lumendata/enso_result.zip')
        self.textures = load_all_textures_from_zip(zip_file)

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(str(sounds_dir / "inst_00_don.wav"))
        self.sound_kat = audio.load_sound(str(sounds_dir / "inst_00_katsu.wav"))
        self.sound_num_up = audio.load_sound(str(sounds_dir / "result" / "SE_RESULT [4].ogg"))
        self.bgm = audio.load_sound(str(sounds_dir / "result" / "JINGLE_SEISEKI [1].ogg"))

    def on_screen_start(self):
        if not self.screen_init:
            self.load_textures()
            self.screen_init = True
            self.song_info = FontText(session_data.song_title, 40).texture
            audio.play_sound(self.bgm)
            self.fade_in = FadeIn(get_current_ms())
            self.gauge = None
            self.score_delay = None
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

    def on_screen_end(self):
        self.screen_init = False
        global_data.songs_played += 1
        audio.play_sound(self.sound_don)
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


    def update(self):
        self.on_screen_start()

        if self.fade_in is not None:
            self.fade_in.update(get_current_ms())
            if self.fade_in.is_finished and self.gauge is None:
                self.gauge = Gauge(get_current_ms(), session_data.result_gauge_length)

        if self.gauge is not None:
            self.gauge.update(get_current_ms())
            if self.gauge.is_finished and self.score_delay is None:
                self.score_delay = get_current_ms() + 1883

        left_dons = get_config()["keybinds"]["left_don"]
        right_dons = get_config()["keybinds"]["right_don"]
        for don in left_dons + right_dons:
            if ray.is_key_pressed(ord(don)):
                if not self.is_skipped:
                    self.is_skipped = True
                    audio.play_sound(self.sound_don)
                else:
                    return self.on_screen_end()
        self.update_score_animation(self.is_skipped)


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
        ray.draw_texture(self.textures['result'][167], 554, 236, ray.WHITE)
        if self.score > -1:
            for i in range(len(str(self.score))):
                ray.draw_texture(self.textures['result'][int(str(self.score)[::-1][i]) + 156], 723-(i*21), 252, ray.WHITE)

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
        ray.draw_texture(self.song_info, 1252 - self.song_info.width, int(35 - self.song_info.height / 2), ray.WHITE)

        ray.draw_texture(self.textures['result'][175], 532, 98, ray.fade(ray.WHITE, 0.75))

        if self.gauge is not None:
            self.gauge.draw(self.textures['result'])

        ray.draw_texture(self.textures['result'][170], 817, 186, ray.WHITE)
        ray.draw_texture(self.textures['result'][171], 817, 227, ray.WHITE)
        ray.draw_texture(self.textures['result'][172], 817, 267, ray.WHITE)
        ray.draw_texture(self.textures['result'][173], 987, 186, ray.WHITE)
        ray.draw_texture(self.textures['result'][174], 981, 227, ray.WHITE)

        self.draw_score_info()
        self.draw_total_score()

        if self.fade_in is not None:
            self.fade_in.draw(self.width, self.height, self.textures['result'][326], self.textures['result'][327])


class FadeIn:
    def __init__(self, current_ms: float):
        self.fadein = Animation(current_ms, 450, 'fade')
        self.fadein.params['initial_opacity'] = 1.0
        self.fadein.params['final_opacity'] = 0.0
        self.fadein.params['delay'] = 100
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

class FontText:
    def __init__(self, text, font_size):
        codepoint_count = ray.ffi.new('int *', 0)
        codepoints_no_dup = set()
        codepoints_no_dup.update(session_data.song_title)
        codepoints = ray.load_codepoints(''.join(codepoints_no_dup), codepoint_count)
        self.font = ray.load_font_ex(str(Path('Graphics/Modified-DFPKanteiryu-XB.ttf')), 32, codepoints, 0)
        self.text = OutlinedText(self.font, str(text), font_size, ray.WHITE, ray.BLACK, outline_thickness=5)

        self.texture = self.text.texture

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
        self.gauge_fade_in = Animation(get_current_ms(), 366, 'fade')
        self.gauge_fade_in.params['initial_opacity'] = 0.0
        self.gauge_fade_in.params['final_opacity'] = 1.0
        self.is_finished = self.gauge_fade_in.is_finished

    def _create_rainbow_anim(self, current_ms):
        anim = Animation(current_ms, (16.67*8) * 3, 'texture_change')
        anim.params['textures'] = []
        for i in range(8):
            anim.params['textures'].append(((16.67* 3)*i, (16.67 * 3)*(i+1), i))
        return anim

    def _create_anim(self, current_ms: float, init: float, final: float):
        anim = Animation(current_ms, 450, 'fade')
        anim.params['initial_opacity'] = init
        anim.params['final_opacity'] = final
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
        if self.gauge_length == 87 and self.rainbow_animation is not None:
            if 0 < self.rainbow_animation.attribute < 8:
                draw_scaled_texture(textures[217 + int(self.rainbow_animation.attribute)], 554, 109, (10/11), color)
            draw_scaled_texture(textures[218 + int(self.rainbow_animation.attribute)], 554, 109, (10/11), color)
        else:
            for i in range(self.gauge_length+1):
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

        if self.gauge_length >= 69:
            draw_scaled_texture(textures[194], 1058, 124, (10/11), color)
            draw_scaled_texture(textures[195], 1182, 115, (10/11), color)
        else:
            draw_scaled_texture(textures[187], 1058, 124, (10/11), color)
            draw_scaled_texture(textures[188], 1182, 115, (10/11), color)
