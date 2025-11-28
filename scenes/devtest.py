import pyray as ray

from libs.screen import Screen
from libs.texture import tex


class DevScreen(Screen):
    def on_screen_start(self):
        super().on_screen_start()

    def on_screen_end(self, next_screen: str):
        return super().on_screen_end(next_screen)

    def update(self):
        super().update()

    def draw(self):
        ray.draw_rectangle(0, 0, tex.screen_width, tex.screen_height, ray.GREEN)
