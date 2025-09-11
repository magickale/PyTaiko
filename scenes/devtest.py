import pyray as ray

from libs.global_objects import Indicator
from libs.utils import get_current_ms


class DevScreen:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.screen_init = False

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True
            self.indicator = Indicator(Indicator.State.SELECT)

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        return next_screen

    def update(self):
        self.on_screen_start()
        self.indicator.update(get_current_ms())
        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            return self.on_screen_end('GAME')

    def draw(self):
        ray.draw_rectangle(0, 0, 1280, 720, ray.GREEN)
        self.indicator.draw(430, 575)

    def draw_3d(self):
        pass
