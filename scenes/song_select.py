import os
from pathlib import Path

import pyray as ray

from libs.audio import audio
from libs.tja import TJAParser
from libs.utils import get_config, session_data


class SongSelectScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.song_list: dict[str, list] = dict()
        self.selected_song = 0
        self.selected_difficulty = 0
        self.selected_index = 0
        for dirpath, dirnames, filenames in os.walk(f'{get_config()["paths"]["tja_path"]}'):
            for filename in filenames:
                if filename.endswith(".tja"):
                    self.song_list[dirpath] = TJAParser(dirpath).get_metadata()

        self.screen_init = False

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(str(sounds_dir / "inst_00_don.wav"))
        self.sound_kat = audio.load_sound(str(sounds_dir / "inst_00_katsu.wav"))

    def on_screen_start(self):
        if not self.screen_init:
            self.load_sounds()
            self.screen_init = True
            self.is_song_select = True
            self.is_difficulty_select = False

    def on_screen_end(self):
        self.screen_init = False
        audio.play_sound(self.sound_don)
        session_data.selected_song = list(self.song_list.keys())[self.selected_song]
        session_data.selected_difficulty = self.selected_difficulty
        return "GAME"

    def update_song_select(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            audio.play_sound(self.sound_don)
            self.is_song_select = False
            self.is_difficulty_select = True
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_UP):
            audio.play_sound(self.sound_kat)
            self.selected_song -= 1
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_DOWN):
            audio.play_sound(self.sound_kat)
            self.selected_song += 1

    def update_difficulty_select(self):
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            return self.on_screen_end()
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_BACKSPACE):
            self.is_song_select = True
            self.is_difficulty_select = False
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_UP):
            audio.play_sound(self.sound_kat)
            self.selected_difficulty = (self.selected_difficulty - 1) % 5
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_DOWN):
            audio.play_sound(self.sound_kat)
            self.selected_difficulty = (self.selected_difficulty + 1) % 5

    def update(self):
        self.on_screen_start()
        if self.is_song_select:
            self.update_song_select()
        elif self.is_difficulty_select:
            return self.update_difficulty_select()

    def draw_song_select(self):
        visible_songs = 36
        song_paths = list(self.song_list.keys())  # Get all paths as a list
        total_songs = len(song_paths)
        start_index = max(0, self.selected_song - visible_songs // 2)
        if start_index + visible_songs > total_songs:
            start_index = max(0, total_songs - visible_songs)
        for i in range(visible_songs):
            if start_index + i < total_songs:  # Ensure we don't go out of bounds
                song_index = start_index + i
                current_path = song_paths[song_index]
                # Get display text from metadata, or use the path as fallback
                display_text = self.song_list[current_path][0]

                if song_index == self.selected_song:
                    color = ray.GREEN
                else:
                    color = ray.BLACK
                ray.draw_text(display_text, 20, (20*i), 20, color)

    def draw_difficulty_select(self):
        difficulties = ["Easy", "Normal", "Hard", "Oni", "Ura"]
        for i in range(len(difficulties)):
            if i == self.selected_difficulty:
                color = ray.GREEN
            else:
                color = ray.BLACK
            ray.draw_text(difficulties[i], 20, (20*i), 20, color)

    def draw(self):
        if self.is_song_select:
            self.draw_song_select()
        elif self.is_difficulty_select:
            self.draw_difficulty_select()
