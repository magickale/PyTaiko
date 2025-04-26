from pathlib import Path

import pyray as ray

from libs.utils import load_texture_from_zip


class EntryScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        self.texture_footer = load_texture_from_zip(Path('Graphics/lumendata/entry.zip'), 'entry_img00375.png')

        self.screen_init = False

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True

    def on_screen_end(self):
        self.screen_init = False
        return "SONG_SELECT"

    def update(self):
        self.on_screen_start()
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            return self.on_screen_end()

    def draw(self):
        ray.draw_texture(self.texture_footer, 0, self.height - 151, ray.WHITE)
