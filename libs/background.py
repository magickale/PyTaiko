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
    """The background class for the game."""
    COLLABS = {
        "A3": libs.bg_collabs.a3.Background,
        "ANIMAL": libs.bg_collabs.animal.Background,
        "BUTTOBURST": libs.bg_collabs.buttoburst.Background
    }
    def __init__(self, player_num: int, bpm: float, scene_preset: str = ''):
        """
        Initialize the background class.

        Args:
            player_num (int): The player number.
            bpm (float): The beats per minute.
            scene_preset (str): The scene preset.
        """
        self.tex_wrapper = TextureWrapper()
        self.tex_wrapper.load_animations('background')
        if player_num == 3:
            if scene_preset == '':
                self.max_dancers = 5
                don_bg_num = random.randint(0, 5)
                self.don_bg = DonBG.create(self.tex_wrapper, don_bg_num, 1)
                self.don_bg_2 = DonBG.create(self.tex_wrapper, don_bg_num, 2)
                self.renda = RendaController(self.tex_wrapper, random.randint(0, 2))
                self.chibi = ChibiController(self.tex_wrapper, random.randint(0, 13), bpm)
                self.bg_normal = None
                self.bg_fever = None
                self.footer = None
                self.fever = None
                self.dancer = None
            else:
                collab_bg = Background.COLLABS[scene_preset](self.tex_wrapper, 1, bpm)
                self.max_dancers = 5
                self.don_bg = collab_bg.don_bg
                self.don_bg_2 = collab_bg.don_bg
                self.bg_normal = None
                self.bg_fever = None
                self.footer = None
                self.fever = None
                self.dancer = None
                self.renda = collab_bg.renda
                self.chibi = collab_bg.chibi
        elif scene_preset == '':
            self.max_dancers = 5
            self.don_bg = DonBG.create(self.tex_wrapper, random.randint(0, 5), player_num)
            self.don_bg_2 = None
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
            self.don_bg_2 = None
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

    def add_chibi(self, bad: bool, player_num: int):
        """
        Add a chibi to the background.

        Args:
            player_num (int): The player number.
            bad (bool): Whether the chibi is bad.
        """
        self.chibi.add_chibi(player_num, bad)

    def add_renda(self):
        """
        Add a renda to the background.
        """
        self.renda.add_renda()

    def update(self, current_time_ms: float, bpm: float, gauge_1p, gauge_2p = None):
        """
        Update the background.

        Args:
            current_time_ms (float): The current time in milliseconds.
            bpm (float): The beats per minute.
            gauge (Gauge): The gauge object.
        """
        if self.dancer is not None:
            clear_threshold = gauge_1p.clear_start[min(gauge_1p.difficulty, 3)]
            if gauge_1p.gauge_length < clear_threshold:
                current_milestone = min(self.max_dancers - 1, int(gauge_1p.gauge_length / (clear_threshold / self.max_dancers)))
            else:
                current_milestone = self.max_dancers
            if current_milestone > self.last_milestone and current_milestone < self.max_dancers:
                self.dancer.add_dancer()
                self.last_milestone = current_milestone
        if self.bg_fever is not None:
            if not self.is_clear and gauge_1p.is_clear:
                self.bg_fever.start()
            if not self.is_rainbow and gauge_1p.is_rainbow and self.fever is not None:
                self.fever.start()
        self.is_clear = gauge_1p.is_clear
        self.is_rainbow = gauge_1p.is_rainbow
        self.don_bg.update(current_time_ms, self.is_clear)
        if self.don_bg_2 is not None:
            self.don_bg_2.update(current_time_ms, gauge_2p.is_clear)
        if self.bg_normal is not None:
            self.bg_normal.update(current_time_ms)
        if self.bg_fever is not None:
            self.bg_fever.update(current_time_ms)
        if self.fever is not None:
            self.fever.update(current_time_ms, bpm)
        if self.dancer is not None:
            self.dancer.update(current_time_ms, bpm)
        self.renda.update(current_time_ms)
        self.chibi.update(current_time_ms, bpm)

    def draw(self):
        """
        Draw the background.
        """
        if self.bg_normal is not None:
            if self.is_clear and not self.bg_fever.transitioned:
                self.bg_normal.draw(self.tex_wrapper)
                self.bg_fever.draw(self.tex_wrapper)
            elif self.is_clear:
                self.bg_fever.draw(self.tex_wrapper)
            else:
                self.bg_normal.draw(self.tex_wrapper)
        self.don_bg.draw(self.tex_wrapper)
        if self.don_bg_2 is not None:
            self.don_bg_2.draw(self.tex_wrapper, y=536)
        self.renda.draw()
        if self.dancer is not None:
            self.dancer.draw(self.tex_wrapper)
        if self.footer is not None:
            self.footer.draw(self.tex_wrapper)
        if self.is_rainbow and self.fever is not None:
            self.fever.draw(self.tex_wrapper)
        self.chibi.draw()

    def unload(self):
        """
        Unload the background.
        """
        self.tex_wrapper.unload_textures()
