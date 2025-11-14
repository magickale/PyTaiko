from libs.bg_objects.bg_normal import BGNormalBase
from libs.global_data import PlayerNum
from libs.texture import TextureWrapper
from libs.bg_objects.don_bg import DonBG1


class Background:
    def __init__(self, tex: TextureWrapper, player_num: PlayerNum, bpm: float, path: str, max_dancers: int):
        self.tex_wrapper = tex
        self.max_dancers = max_dancers
        self.don_bg = DonBG1(self.tex_wrapper, 0, 1, path)
        self.bg_normal = BGNormalBase(self.tex_wrapper, 0, path)
        self.bg_fever = None
        self.footer = None
        self.fever = None
        self.dancer = None
        self.renda = None
        self.chibi = None
