import pyray as ray

from libs.audio import audio
from libs.utils import global_data


class ResultScreen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.sound_don = audio.load_sound('Sounds\\inst_00_don.wav')

    def update(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            global_data.songs_played += 1
            audio.play_sound(self.sound_don)
            return "SONG_SELECT"

    def draw(self):
        ray.draw_text(f"{global_data.selected_song}", 100, 60, 20, ray.BLACK)
        ray.draw_text(f"SCORE: {global_data.result_score}", 100, 80, 20, ray.BLACK)
        ray.draw_text(f"GOOD: {global_data.result_good}", 100, 100, 20, ray.BLACK)
        ray.draw_text(f"OK: {global_data.result_ok}", 100, 120, 20, ray.BLACK)
        ray.draw_text(f"BAD: {global_data.result_bad}", 100, 140, 20, ray.BLACK)
