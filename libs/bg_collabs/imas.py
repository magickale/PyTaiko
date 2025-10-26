from libs.animation import Animation
from libs.bg_objects.bg_fever import BGFeverBase
from libs.bg_objects.bg_normal import BGNormalBase
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.dancer import BaseDancerGroup
from libs.bg_objects.fever import BaseFever
from libs.bg_objects.footer import Footer
from libs.bg_objects.renda import RendaController
from libs.texture import TextureWrapper
from libs.bg_objects.don_bg import DonBGBase


class Background:
    def __init__(self, tex: TextureWrapper, player_num: int, bpm: float):
        self.tex_wrapper = tex
        path = 'background/collab/imas'
        self.max_dancers = 5
        self.don_bg = DonBGBase(self.tex_wrapper, 0, player_num, path)
        self.bg_normal = BGNormalBase(self.tex_wrapper, 0, path)
        self.bg_fever = BGFeverBase(self.tex_wrapper, 0, path)
        self.footer = Footer(self.tex_wrapper, 0, path)
        self.fever = Fever(self.tex_wrapper, 0, bpm, path)
        self.dancer = BaseDancerGroup(self.tex_wrapper, 0, bpm, self.max_dancers, path)
        self.renda = RendaController(self.tex_wrapper, 0, path)
        self.chibi = ChibiController(self.tex_wrapper, 0, bpm, path)

class Fever(BaseFever):
    def __init__(self, tex: TextureWrapper, player_num: int, bpm: float, path: str):
        super().__init__(tex, player_num, bpm, path)
        self.texture_change = Animation.create_texture_change(120000 / bpm, textures=[(0, (120000 / bpm) / 2, 0), ((120000 / bpm) / 2, 120000 / bpm, 1)])
        self.texture_change.loop = True
        self.texture_change.start()

    def update(self, current_time_ms: float, bpm: float):
        super().update(current_time_ms, bpm)
        self.texture_change.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'overlay', y=self.bounce_down.attribute-self.bounce_up.attribute, frame=self.texture_change.attribute)

class BGNormal(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int, path: str):
        super().__init__(tex, index, path)

    def update(self, current_time_ms: float, bpm: float):
        super().update(current_time_ms, bpm)

    def draw(self, tex: TextureWrapper):
        pass
