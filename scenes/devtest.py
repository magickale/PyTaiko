import pyray as ray

from libs.texture import tex
from libs.utils import get_current_ms
from scenes.song_select import ScoreHistory


class DevScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.screen_init = False
        tex.load_screen_textures('song_select')
        self.history = ScoreHistory({0: (583892, 0, 0, 0),
                                     1: (234941, 0, 0, 0),
                                     2: (867847, 0, 0, 0),
                                     3: (485589, 0, 0, 0),
                                     4: (1584395, 0, 0, 0)}, get_current_ms())

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        return next_screen

    def update(self):
        self.on_screen_start()
        self.history.update(get_current_ms())
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            return self.on_screen_end('RESULT')

    def draw(self):
        self.history.draw()

    def draw_3d(self):
        pass
