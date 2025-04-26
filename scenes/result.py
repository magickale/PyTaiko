from pathlib import Path

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    load_all_textures_from_zip,
)


def draw_scaled_texture(texture, x: int, y: int, scale: float, color: ray.Color) -> None:
    width = texture.width
    height = texture.height
    src_rect = ray.Rectangle(0, 0, width, height)
    dst_rect = ray.Rectangle(x, y, width*scale, height*scale)
    ray.draw_texture_pro(texture, src_rect, dst_rect, ray.Vector2(0, 0), 0, color)

class ResultScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(str(sounds_dir / "inst_00_don.wav"))
        self.sound_kat = audio.load_sound(str(sounds_dir / "inst_00_katsu.wav"))
        self.bgm = audio.load_sound(str(sounds_dir / "result" / "JINGLE_SEISEKI [1].ogg"))

        zip_file = Path('Graphics/lumendata/enso_result.zip')
        self.textures = load_all_textures_from_zip(zip_file)

        self.song_info = FontText(global_data.song_title, 40).texture
        self.screen_init = False

        self.fade_in = None

        self.bgm_volume = 1.0

    def on_screen_start(self):
        if not self.screen_init:
            self.textures = load_all_textures_from_zip(Path('Graphics/lumendata/enso_result.zip'))
            self.screen_init = True
            self.song_info = FontText(global_data.song_title, 40).texture
            self.bgm_volume = 1.0
            audio.play_sound(self.bgm)
            self.fade_in = FadeIn(get_current_ms())

    def on_screen_end(self):
        self.screen_init = False
        global_data.songs_played += 1
        audio.play_sound(self.sound_don)
        for zip in self.textures:
            for texture in self.textures[zip]:
                ray.unload_texture(texture)
        audio.stop_sound(self.bgm)
        return "SONG_SELECT"

    def update(self):
        self.on_screen_start()
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            return self.on_screen_end()

        if self.fade_in is not None:
            self.fade_in.update(get_current_ms())

    def draw_score_info(self):
        for i in range(len(str(global_data.result_good))):
            ray.draw_texture(self.textures['result'][int(str(global_data.result_good)[::-1][i]) + 136], 943-(i*24), 186, ray.WHITE)
        for i in range(len(str(global_data.result_ok))):
            ray.draw_texture(self.textures['result'][int(str(global_data.result_ok)[::-1][i]) + 136], 943-(i*24), 227, ray.WHITE)
        for i in range(len(str(global_data.result_bad))):
            ray.draw_texture(self.textures['result'][int(str(global_data.result_bad)[::-1][i]) + 136], 943-(i*24), 267, ray.WHITE)

    def draw_total_score(self):
        ray.draw_texture(self.textures['result'][167], 554, 236, ray.WHITE)
        for i in range(len(str(global_data.result_score))):
            ray.draw_texture(self.textures['result'][int(str(global_data.result_score)[::-1][i]) + 156], 723-(i*21), 252, ray.WHITE)

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

        draw_scaled_texture(self.textures['result'][217], 554, 109, (10/11), ray.WHITE)
        draw_scaled_texture(self.textures['result'][226], 554, 109, (10/11), ray.fade(ray.WHITE, 0.15))
        draw_scaled_texture(self.textures['result'][176], 1185, 116, (10/11), ray.WHITE)
        draw_scaled_texture(self.textures['result'][187], 1058, 124, (10/11), ray.WHITE)
        draw_scaled_texture(self.textures['result'][188], 1182, 115, (10/11), ray.WHITE)

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

    def update(self, current_ms: float):
        self.fadein.update(current_ms)
        self.fade = ray.fade(ray.WHITE, self.fadein.attribute)

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
        codepoints_no_dup.update(global_data.song_title)
        codepoints = ray.load_codepoints(''.join(codepoints_no_dup), codepoint_count)
        self.font = ray.load_font_ex('Graphics\\Modified-DFPKanteiryu-XB.ttf', 32, codepoints, 0)
        self.text = OutlinedText(self.font, str(text), font_size, ray.WHITE, ray.BLACK, outline_thickness=5)

        self.texture = self.text.texture
