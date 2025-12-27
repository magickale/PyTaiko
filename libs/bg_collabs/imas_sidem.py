from libs.animation import Animation
from libs.bg_collabs.imas import Fever
from libs.bg_objects.bg_fever import BGFeverBase
from libs.bg_objects.bg_normal import BGNormalBase
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.dancer import BaseDancerGroup
from libs.bg_objects.don_bg import DonBGBase
from libs.bg_objects.footer import Footer
from libs.bg_objects.renda import RendaController
from libs.global_data import PlayerNum
from libs.texture import TextureWrapper


class Background:
    def __init__(self, tex: TextureWrapper, player_num: PlayerNum, bpm: float, path: str, max_dancers: int):
        self.tex_wrapper = tex
        self.max_dancers = max_dancers
        self.don_bg = DonBG(self.tex_wrapper, 0, player_num, path)
        self.bg_normal = BGNormal(self.tex_wrapper, 0, path)
        self.bg_fever = BGFever(self.tex_wrapper, 0, path)
        self.footer = Footer(self.tex_wrapper, 0, path)
        self.fever = Fever(self.tex_wrapper, 0, bpm, path)
        self.dancer = BaseDancerGroup(self.tex_wrapper, 0, bpm, self.max_dancers, path)
        self.renda = RendaController(self.tex_wrapper, 0, path)
        self.chibi = ChibiController(self.tex_wrapper, 0, bpm, path)

class DonBG(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: PlayerNum, path: str):
        super().__init__(tex, index, player_num, path)
        self.move = Animation.create_move(3000, total_distance=-tex.textures[self.name]['background'].width)
        self.move.loop = True
        self.move.start()

    def _draw_textures(self, tex: TextureWrapper, fade: float, y: float):
        for i in range(int(5 * tex.screen_scale)):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*tex.textures[self.name]['background'].width)+self.move.attribute, y=y)

class BGNormal(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int, path: str):
        super().__init__(tex, index, path)
        self.screen_change = Animation.create_texture_change(8000, textures=[(0, 2000, 0), (2000, 4000, 1), (4000, 6000, 2), (6000, 8000, 3)])
        self.screen_change.loop = True
        self.screen_change.start()

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.screen_change.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'screen', frame=self.screen_change.attribute)
        tex.draw_texture(self.name, 'overlay')

class BGFever(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int, path: str):
        super().__init__(tex, index, path)
        self.screen_change = Animation.create_texture_change(8000, textures=[(0, 2000, 0), (2000, 4000, 1), (4000, 6000, 2), (6000, 8000, 3)])
        self.screen_change.loop = True
        self.screen_change.start()
        self.transitioned = True

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.screen_change.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'screen', frame=self.screen_change.attribute)
        tex.draw_texture(self.name, 'overlay')
        tex.draw_texture(self.name, 'overlay_2')
