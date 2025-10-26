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

import pyray as ray


class Background:
    def __init__(self, tex: TextureWrapper, player_num: int, bpm: float, path: str, max_dancers: int):
        self.tex_wrapper = tex
        self.max_dancers = max_dancers
        self.don_bg = DonBGBase(self.tex_wrapper, 0, player_num, path)
        self.bg_normal = BGNormal(self.tex_wrapper, 0, path)
        self.bg_fever = BGFever(self.tex_wrapper, 0, path)
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
        self.overlay_fade = Animation.create_fade(1000, initial_opacity=0.0, final_opacity=1.0, reverse_delay=500, delay=500)
        self.overlay_fade.loop = True
        self.overlay_fade.start()
        self.spotlight_colors = [ray.Color(0, 255, 255, 255), ray.YELLOW, ray.MAGENTA, ray.Color(0, 255, 255, 255), ray.YELLOW]

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.overlay_fade.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        super().draw(tex)
        tex.draw_texture(self.name, 'overlay', fade=self.overlay_fade.attribute)
        for i in range(5):
            if i % 2 == 0:
                fade = min(0.5, self.overlay_fade.attribute)
            else:
                fade = min(0.5, 1 - self.overlay_fade.attribute)
            tex.draw_texture(self.name, 'spotlight', index=i, color=self.spotlight_colors[i], fade=fade)

class BGFever(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int, path: str):
        super().__init__(tex, index, path)
        self.overlay_fade = Animation.create_fade(1000, initial_opacity=0.0, final_opacity=1.0, reverse_delay=500, delay=500)
        self.overlay_fade.loop = True
        self.overlay_fade.start()
        self.spotlight_colors = [ray.Color(0, 255, 255, 255), ray.YELLOW, ray.MAGENTA, ray.Color(0, 255, 255, 255), ray.YELLOW]

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.overlay_fade.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'overlay', fade=self.overlay_fade.attribute)
        tex.draw_texture(self.name, 'light_orange', fade=self.overlay_fade.attribute)
        tex.draw_texture(self.name, 'light_green', fade=1 - self.overlay_fade.attribute)
        for i in range(5):
            if i % 2 == 0:
                fade = min(0.5, self.overlay_fade.attribute)
            else:
                fade = min(0.5, 1 - self.overlay_fade.attribute)
            tex.draw_texture(self.name, 'spotlight', index=i, color=self.spotlight_colors[i], fade=fade)
