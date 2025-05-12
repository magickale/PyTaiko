import os
from pathlib import Path

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.tja import TJAParser
from libs.utils import (
    OutlinedText,
    get_config,
    get_current_ms,
    load_all_textures_from_zip,
    session_data,
)


class SongSelectScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.song_list: dict[str, list] = dict()
        self.song_name_textures: list[OutlinedText] = []
        self.selected_song = 0
        self.selected_difficulty = 0
        self.selected_index = 0

        self.screen_init = False

    def _load_font_for_text(self, text: str) -> ray.Font:
        codepoint_count = ray.ffi.new('int *', 0)
        unique_codepoints = set(text)
        codepoints = ray.load_codepoints(''.join(unique_codepoints), codepoint_count)
        return ray.load_font_ex(str(Path('Graphics/Modified-DFPKanteiryu-XB.ttf')), 32, codepoints, 0)

    def load_textures(self):
        self.textures = load_all_textures_from_zip(Path('Graphics/lumendata/song_select.zip'))

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(str(sounds_dir / "inst_00_don.wav"))
        self.sound_kat = audio.load_sound(str(sounds_dir / "inst_00_katsu.wav"))

    def on_screen_start(self):
        if not self.screen_init:
            self.load_textures()
            self.load_sounds()
            for dirpath, dirnames, filenames in os.walk(f'{get_config()["paths"]["tja_path"]}'):
                for filename in filenames:
                    if filename.endswith(".tja"):
                        self.song_list[dirpath] = TJAParser(dirpath).get_metadata()
                        name = self.song_list[dirpath][1]
                        if name == '':
                            name = self.song_list[dirpath][0]
                        if len(self.song_name_textures) < 17:
                            font = self._load_font_for_text(name)
                            self.song_name_textures.append(OutlinedText(font, name, 40, ray.WHITE, ray.BLACK, outline_thickness=4, vertical=True))
            self.screen_init = True
            self.is_song_select = True
            self.is_difficulty_select = False
            self.background_move = Animation.create_move(15000, start_position=0, total_distance=1280)

    def on_screen_end(self):
        self.screen_init = False
        audio.play_sound(self.sound_don)
        session_data.selected_song = list(self.song_list.keys())[self.selected_song]
        session_data.selected_difficulty = self.selected_difficulty
        for zip in self.textures:
            for texture in self.textures[zip]:
                ray.unload_texture(texture)
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
        self.background_move.update(get_current_ms())
        if self.background_move.is_finished:
            self.background_move = Animation.create_move(15000, start_position=0, total_distance=1280)
        if self.is_song_select:
            self.update_song_select()
        elif self.is_difficulty_select:
            return self.update_difficulty_select()

    def draw_box(self, x: int, y: int, texture_index: int):
        ray.draw_texture(self.textures['song_select'][texture_index+1], x, y, ray.WHITE)
        for i in range(0, self.textures['song_select'][texture_index].width * 4, self.textures['song_select'][texture_index].width):
            ray.draw_texture(self.textures['song_select'][texture_index], (x+32)+i, y, ray.WHITE)
        ray.draw_texture(self.textures['song_select'][texture_index+2], x+64, y, ray.WHITE)
        ray.draw_texture(self.textures['song_select'][texture_index+3], x+12, y+16, ray.WHITE)

    def draw_song_select(self):
        texture = self.textures['song_select'][784]
        for i in range(0, texture.width * 4, texture.width):
            ray.draw_texture(self.textures['song_select'][784], i - int(self.background_move.attribute), 0, ray.WHITE)
        ray.draw_texture(self.textures['song_select'][244], 5, 5, ray.WHITE)
        ray.draw_texture(self.textures['song_select'][394], 0, self.height - self.textures['song_select'][394].height, ray.WHITE)

        for i in range(-1, 15):
            self.draw_box(44 + (i*100), 95, 620)
            texture = self.song_name_textures[i+1]
            src = ray.Rectangle(0, 0, texture.texture.width, texture.texture.height)
            dest = ray.Rectangle((91 + (i*100)) - texture.texture.width / 2, 130, texture.texture.width, min(texture.texture.height, 417))
            texture.draw(src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

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
