from libs.animation import Animation
from libs.bg_objects.bg_normal import BGNormalBase
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.don_bg import DonBG6
from libs.bg_objects.footer import Footer
from libs.texture import TextureWrapper

class Background:
    def __init__(self, tex: TextureWrapper, player_num: int, bpm: float, path: str, max_dancers: int):
        self.tex_wrapper = tex
        self.max_dancers = max_dancers
        self.don_bg = DonBG(self.tex_wrapper, 0, 1, path)
        self.bg_normal = BGNormalBase(self.tex_wrapper, 0, path)
        self.bg_fever = None
        self.footer = Footer(self.tex_wrapper, 0, path)
        self.fever = None
        self.dancer = None
        self.renda = None
        self.chibi = ChibiController(self.tex_wrapper, 2, bpm, path)

class DonBG(DonBG6):
    def __init__(self, tex: TextureWrapper, player_num: int, bpm: float, path: str):
        super().__init__(tex, player_num, bpm, path)
        self.overlay_move_2 = Animation.create_move(8000, total_distance=-760)
        self.overlay_move_2.loop = True
        self.overlay_move_2.start()

    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move_2.update(current_time_ms)

    def _draw_textures(self, tex: TextureWrapper, fade: float, y: float):
        tex.draw_texture(self.name, 'background')
        for i in range(3):
            tex.draw_texture(self.name, 'bg_overlay', x=(i*464), y=y)
        for i in range(3):
            tex.draw_texture(self.name, 'bg_overlay_2', x=(i*760)+(self.overlay_move_2.attribute), y=y)
        for i in range(0, 6, 2):
            tex.draw_texture(self.name, 'overlay_1', x=(i*264) + self.move.attribute*3, y=-self.move.attribute*0.85+y)
        tex.draw_texture(self.name, 'bg_overlay_3')
        for i in range(5):
            tex.draw_texture(self.name, 'overlay_2', x=(i*328)+self.move.attribute, y=self.overlay_move.attribute+y)
