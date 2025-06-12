from pathlib import Path

import pyray as ray

from libs.utils import is_l_don_pressed, is_r_don_pressed, load_texture_from_zip


class EntryScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        self.texture_footer = load_texture_from_zip(Path('Graphics/lumendata/entry.zip'), 'entry_img00375.png')

        self.screen_init = False

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        return next_screen

    def update(self):
        self.on_screen_start()
        if is_l_don_pressed() or is_r_don_pressed():
            return self.on_screen_end("SONG_SELECT")
        if ray.is_key_pressed(ray.KeyboardKey.KEY_F1):
            return self.on_screen_end("SETTINGS")

    def draw(self):
        ray.draw_texture(self.texture_footer, 0, self.height - 151, ray.WHITE)
