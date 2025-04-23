import os

import pyray as ray

from libs.audio import audio
from libs.utils import get_config, global_data


class SongSelectScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.is_song_select = True
        self.is_difficulty_select = False
        self.song_list: list[str] = []
        self.selected_song = 0
        self.selected_difficulty = 0
        self.selected_index = 0
        self.sound_don = audio.load_sound('Sounds\\inst_00_don.wav')
        self.sound_kat = audio.load_sound('Sounds\\inst_00_katsu.wav')
        for dirpath, dirnames, filenames in os.walk(f'{get_config()["paths"]["tja_path"]}'):
            for filename in filenames:
                if filename.endswith(".tja"):
                    self.song_list.append(dirpath)

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
            audio.play_sound(self.sound_don)
            global_data.selected_song = self.song_list[self.selected_song]
            global_data.selected_difficulty = self.selected_difficulty
            global_data.start_song = True
            self.is_song_select = True
            self.is_difficulty_select = False
            return "GAME"
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
        if self.is_song_select:
            self.update_song_select()
        elif self.is_difficulty_select:
            return self.update_difficulty_select()

    def draw_song_select(self):
        visible_songs = 36
        total_songs = len(self.song_list)
        start_index = max(0, self.selected_song - visible_songs // 2)

        if start_index + visible_songs > total_songs:
            start_index = max(0, total_songs - visible_songs)

        for i in range(visible_songs):
            song_index = (start_index + i) % total_songs

            if song_index == self.selected_song:
                color = ray.GREEN
            else:
                color = ray.BLACK

            ray.draw_text(self.song_list[song_index], 20, (20*i), 20, color)

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
