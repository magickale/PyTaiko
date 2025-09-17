import random

import libs.bg_collabs
from libs.bg_objects.bg_fever import BGFever
from libs.bg_objects.bg_normal import BGNormal
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.dancer import Dancer
from libs.bg_objects.don_bg import DonBG
from libs.bg_objects.fever import Fever
from libs.bg_objects.footer import Footer
from libs.bg_objects.renda import RendaController
from libs.texture import TextureWrapper

class Background:
    COLLABS = {
        "A3": libs.bg_collabs.a3.Background,
        "ANIMAL": libs.bg_collabs.animal.Background
    }
    def __init__(self, player_num: int, bpm: float, scene_preset: str = ''):
        self.tex_wrapper = TextureWrapper()
        self.tex_wrapper.load_animations('background')
        if scene_preset == '':
            self.max_dancers = 5
            self.don_bg = DonBG.create(self.tex_wrapper, random.randint(0, 5), player_num)
            self.bg_normal = BGNormal.create(self.tex_wrapper, random.randint(0, 4))
            self.bg_fever = BGFever.create(self.tex_wrapper, random.randint(0, 3))
            self.footer = Footer(self.tex_wrapper, random.randint(0, 2))
            self.fever = Fever.create(self.tex_wrapper, random.randint(0, 3), bpm)
            self.dancer = Dancer.create(self.tex_wrapper, random.randint(0, 20), bpm)
            self.renda = RendaController(self.tex_wrapper, random.randint(0, 2))
            self.chibi = ChibiController(self.tex_wrapper, random.randint(0, 13), bpm)
        else:
            collab_bg = Background.COLLABS[scene_preset](self.tex_wrapper, player_num, bpm)
            self.max_dancers = collab_bg.max_dancers
            self.don_bg = collab_bg.don_bg
            self.bg_normal = collab_bg.bg_normal
            self.bg_fever = collab_bg.bg_fever
            self.footer = collab_bg.footer
            self.fever = collab_bg.fever
            self.dancer = collab_bg.dancer
            self.renda = collab_bg.renda
            self.chibi = collab_bg.chibi
        self.is_clear = False
        self.is_rainbow = False
        self.last_milestone = 0

    def add_chibi(self, bad: bool):
        self.chibi.add_chibi(bad)

    def add_renda(self):
        self.renda.add_renda()

    def update(self, current_time_ms: float, bpm: float, gauge):
        clear_threshold = gauge.clear_start[min(gauge.difficulty, 3)]
        if gauge.gauge_length < clear_threshold:
            current_milestone = min(self.max_dancers - 1, int(gauge.gauge_length / (clear_threshold / self.max_dancers)))
        else:
            current_milestone = self.max_dancers
        if current_milestone > self.last_milestone and current_milestone < self.max_dancers:
            self.dancer.add_dancer()
            self.last_milestone = current_milestone
        if not self.is_clear and gauge.is_clear:
            self.bg_fever.start()
        if not self.is_rainbow and gauge.is_rainbow and self.fever is not None:
            self.fever.start()
        self.is_clear = gauge.is_clear
        self.is_rainbow = gauge.is_rainbow
        self.don_bg.update(current_time_ms, self.is_clear)
        self.bg_normal.update(current_time_ms)
        self.bg_fever.update(current_time_ms)
        if self.fever is not None:
            self.fever.update(current_time_ms, bpm)
        self.dancer.update(current_time_ms, bpm)
        self.renda.update(current_time_ms)
        self.chibi.update(current_time_ms, bpm)
    def draw(self):
        if self.is_clear and not self.bg_fever.transitioned:
            self.bg_normal.draw(self.tex_wrapper)
            self.bg_fever.draw(self.tex_wrapper)
        elif self.is_clear:
            self.bg_fever.draw(self.tex_wrapper)
        else:
            self.bg_normal.draw(self.tex_wrapper)
        self.don_bg.draw(self.tex_wrapper)
        self.renda.draw()
        self.dancer.draw(self.tex_wrapper)
        if self.footer is not None:
            self.footer.draw(self.tex_wrapper)
        if self.is_rainbow and self.fever is not None:
            self.fever.draw(self.tex_wrapper)
        self.chibi.draw()
    def unload(self):
        self.tex_wrapper.unload_textures()
