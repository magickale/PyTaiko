import os

import pyray as ray

from libs.audio import audio
from libs.utils import GlobalData, get_config


class SongSelectScreen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.is_song_select = True
        self.is_difficulty_select = False
        self.song_list = []
        self.selected_song = 0
        self.selected_difficulty = 0
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
            GlobalData.selected_song = self.song_list[self.selected_song]
            GlobalData.selected_difficulty = self.selected_difficulty
            GlobalData.start_song = True
            self.is_song_select = True
            self.is_difficulty_select = False
            return "GAME"
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_BACKSPACE):
            self.is_song_select = True
            self.is_difficulty_select = False
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_UP):
            audio.play_sound(self.sound_kat)
            self.selected_difficulty -= 1
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_DOWN):
            audio.play_sound(self.sound_kat)
            self.selected_difficulty += 1

    def update(self):
        if self.is_song_select:
            self.update_song_select()
        elif self.is_difficulty_select:
            return self.update_difficulty_select()

    def draw_song_select(self):
        for i in range(len(self.song_list)):
            if i == self.selected_song:
                color = ray.GREEN
            else:
                color = ray.BLACK
            ray.draw_text(self.song_list[i], 20, (20*i), 20, color)

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
