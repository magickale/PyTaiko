import random

from libs.bg_objects.bg_fever import BGFever
from libs.bg_objects.bg_normal import BGNormal
from libs.bg_objects.dancer import Dancer
from libs.bg_objects.don_bg import DonBG
from libs.bg_objects.fever import Fever
from libs.texture import TextureWrapper


class Background:
    def __init__(self, player_num: int, bpm: float):
        self.tex_wrapper = TextureWrapper()
        self.tex_wrapper.load_animations('background')
        self.donbg = DonBG.create(self.tex_wrapper, random.randint(0, 5), player_num)
        self.bg_normal = BGNormal.create(self.tex_wrapper, random.randint(0, 4))
        self.bg_fever = BGFever.create(self.tex_wrapper, random.randint(0, 3))
        self.footer = Footer(self.tex_wrapper, random.randint(0, 2))
        self.fever = Fever.create(self.tex_wrapper, random.randint(0, 3), bpm)
        self.dancer = Dancer.create(self.tex_wrapper, 0, bpm)
        self.is_clear = False
        self.is_rainbow = False
        self.last_milestone = 0
    def update(self, current_time_ms: float, bpm: float, gauge):
        is_clear = gauge.gauge_length > gauge.clear_start[min(gauge.difficulty, 3)]
        is_rainbow = gauge.gauge_length == gauge.gauge_max
        clear_threshold = gauge.clear_start[min(gauge.difficulty, 3)]
        if gauge.gauge_length < clear_threshold:
            current_milestone = min(4, int(gauge.gauge_length / (clear_threshold / 4)))
        else:
            current_milestone = 5
        if current_milestone > self.last_milestone and current_milestone <= 5:
            self.dancer.add_dancer()
            self.last_milestone = current_milestone
        if not self.is_clear and is_clear:
            self.bg_fever.start()
        if not self.is_rainbow and is_rainbow:
            self.fever.start()
        self.is_clear = is_clear
        self.is_rainbow = is_rainbow
        self.donbg.update(current_time_ms, self.is_clear)
        self.bg_normal.update(current_time_ms)
        self.bg_fever.update(current_time_ms)
        self.fever.update(current_time_ms, bpm)
        self.dancer.update(current_time_ms, bpm)
    def draw(self):
        self.bg_normal.draw(self.tex_wrapper)
        if self.is_clear:
            self.bg_fever.draw(self.tex_wrapper)
        self.donbg.draw(self.tex_wrapper)
        self.dancer.draw(self.tex_wrapper)
        self.footer.draw(self.tex_wrapper)
        if self.is_rainbow:
            self.fever.draw(self.tex_wrapper)
    def unload(self):
        self.tex_wrapper.unload_textures()

class Footer:
    def __init__(self, tex: TextureWrapper, index: int):
        self.index = index
        tex.load_zip('background', 'footer')
    def draw(self, tex: TextureWrapper):
        tex.draw_texture('footer', str(self.index))
