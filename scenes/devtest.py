import pyray as ray

from libs.utils import global_data, session_data


class DevScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.screen_init = False

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True
            session_data.result_score = 961000
            session_data.result_good = 100
            session_data.result_max_combo = 20
            session_data.result_total_drumroll = 40

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        return next_screen

    def update(self):
        self.on_screen_start()

        if ray.is_key_pressed(ray.KeyboardKey.KEY_ENTER):
            return self.on_screen_end('RESULT')

    def draw(self):
        pass

    def draw_3d(self):
        pass
