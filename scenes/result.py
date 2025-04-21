import pyray as ray

from libs.audio import audio
from libs.utils import GlobalData


class ResultScreen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.sound_don = audio.load_sound('Sounds\\inst_00_don.wav')

    def update(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            audio.play_sound(self.sound_don)
            return "SONG_SELECT"

    def draw(self):
        ray.draw_text(f"{GlobalData.selected_song}", 100, 60, 20, ray.BLACK)
        ray.draw_text(f"SCORE: {GlobalData.result_score}", 100, 80, 20, ray.BLACK)
        ray.draw_text(f"GOOD: {GlobalData.result_good}", 100, 100, 20, ray.BLACK)
        ray.draw_text(f"OK: {GlobalData.result_ok}", 100, 120, 20, ray.BLACK)
        ray.draw_text(f"BAD: {GlobalData.result_bad}", 100, 140, 20, ray.BLACK)
