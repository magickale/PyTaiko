import pyray as ray

from libs.utils import get_current_ms
from libs.texture import tex
from scenes.game import GogoTime, NoteArc


class DevScreen:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.screen_init = False
        self.length = 100

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True
            tex.load_screen_textures('game')
            self.obj = GogoTime()

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        return next_screen

    def update(self):
        self.on_screen_start()
        self.obj.update(get_current_ms())
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            return self.on_screen_end('GAME')
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_SPACE):
            self.obj = GogoTime()

    def draw(self):
        ray.draw_rectangle(0, 0, 1280, 720, ray.GREEN)
        self.obj.draw()

    def draw_3d(self):
        pass
