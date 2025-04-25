import pyray as ray

from libs.audio import audio
from libs.utils import (
    OutlinedText,
    global_data,
    load_all_textures_from_zip,
    load_image_from_zip,
)


def draw_scaled_texture(texture, x: int, y: int, scale: float, color: ray.Color) -> None:
    width = texture.width
    height = texture.height
    src_rect = ray.Rectangle(0, 0, width, height)
    dst_rect = ray.Rectangle(x, y, width*scale, height*scale)
    ray.draw_texture_pro(texture, src_rect, dst_rect, ray.Vector2(0, 0), 0, color)

class ResultScreen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.sound_don = audio.load_sound('Sounds\\inst_00_don.wav')

        zip_file = 'Graphics\\lumendata\\enso_result.zip'
        self.textures = load_all_textures_from_zip(zip_file)

        ray.unload_texture(self.textures['result'][327])
        image = load_image_from_zip(zip_file, 'result_img00327.png')
        ray.image_resize(image, 1280, 144)
        self.textures['result'][327] = ray.load_texture_from_image(image)

        self.text_generated = False
        self.song_info = FontText(global_data.song_title, 40).texture

    def update(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            global_data.songs_played += 1
            audio.play_sound(self.sound_don)
            return "SONG_SELECT"

        if not self.text_generated and global_data.song_title != '':
            self.song_info = FontText(global_data.song_title, 40).texture
            self.text_generated = True

    def draw(self):
        x = 0
        while x < self.width:
            ray.draw_texture(self.textures['result'][326], x, 0 - self.textures['result'][326].height//2, ray.WHITE)
            ray.draw_texture(self.textures['result'][326], x, self.height - self.textures['result'][326].height//2, ray.WHITE)
            x += self.textures['result'][326].width
        ray.draw_texture(self.textures['result'][327], 0, 0 - self.textures['result'][327].height//2, ray.WHITE)
        ray.draw_texture(self.textures['result'][327], 0, self.height - self.textures['result'][327].height + self.textures['result'][327].height//2, ray.WHITE)


        ray.draw_text(f"{global_data.selected_song}", 100, 60, 20, ray.BLACK)
        ray.draw_text(f"SCORE: {global_data.result_score}", 100, 80, 20, ray.BLACK)
        ray.draw_text(f"GOOD: {global_data.result_good}", 100, 100, 20, ray.BLACK)
        ray.draw_text(f"OK: {global_data.result_ok}", 100, 120, 20, ray.BLACK)
        ray.draw_text(f"BAD: {global_data.result_bad}", 100, 140, 20, ray.BLACK)

        ray.draw_texture(self.textures['result'][330], -5, 3, ray.WHITE)
        ray.draw_texture(self.textures['result'][(global_data.songs_played % 4) + 331], 232, 4, ray.WHITE)
        ray.draw_texture(self.song_info, 1252 - self.song_info.width, int(35 - self.song_info.height / 2), ray.WHITE)

        ray.draw_texture(self.textures['result'][175], 532, 98, ray.fade(ray.WHITE, 0.75))

        draw_scaled_texture(self.textures['result'][217], 554, 109, (10/11), ray.WHITE)
        draw_scaled_texture(self.textures['result'][226], 554, 109, (10/11), ray.fade(ray.WHITE, 0.15))
        draw_scaled_texture(self.textures['result'][176], 1185, 116, (10/11), ray.WHITE)
        draw_scaled_texture(self.textures['result'][187], 1058, 124, (10/11), ray.WHITE)
        draw_scaled_texture(self.textures['result'][188], 1182, 115, (10/11), ray.WHITE)

class FontText:
    def __init__(self, text, font_size):
        codepoint_count = ray.ffi.new('int *', 0)
        codepoints_no_dup = set()
        codepoints_no_dup.update(global_data.song_title)
        codepoints = ray.load_codepoints(''.join(codepoints_no_dup), codepoint_count)
        self.font = ray.load_font_ex('Graphics\\Modified-DFPKanteiryu-XB.ttf', 32, codepoints, 0)
        self.text = OutlinedText(self.font, str(text), font_size, ray.WHITE, ray.BLACK, outline_thickness=5)

        self.texture = self.text.texture
