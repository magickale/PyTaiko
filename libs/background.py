import random

from libs.bg_objects.bg_fever import BGFever
from libs.bg_objects.bg_normal import BGNormal
from libs.bg_objects.don_bg import DonBG
from libs.texture import TextureWrapper


class Background:
    def __init__(self, player_num: int):
        self.tex_wrapper = TextureWrapper()
        self.tex_wrapper.load_animations('background')
        self.donbg = DonBG.create(self.tex_wrapper, random.randint(0, 5), player_num)
        self.bg_normal = BGNormal.create(self.tex_wrapper, random.randint(0, 4))
        self.bg_fever = BGFever.create(self.tex_wrapper, random.randint(0, 3))
        self.footer = Footer(self.tex_wrapper, random.randint(0, 2))
        self.is_clear = False
    def update(self, current_time_ms: float, is_clear: bool):
        if not self.is_clear and is_clear:
            self.bg_fever.start()
        self.is_clear = is_clear
        self.donbg.update(current_time_ms, self.is_clear)
        self.bg_normal.update(current_time_ms)
        self.bg_fever.update(current_time_ms)
    def draw(self):
        self.bg_normal.draw(self.tex_wrapper)
        if self.is_clear:
            self.bg_fever.draw(self.tex_wrapper)
        self.footer.draw(self.tex_wrapper)
        self.donbg.draw(self.tex_wrapper)

    def unload(self):
        self.tex_wrapper.unload_textures()

class Footer:
    def __init__(self, tex: TextureWrapper, index: int):
        self.index = index
        tex.load_zip('background', 'footer')
    def draw(self, tex: TextureWrapper):
        tex.draw_texture('footer', str(self.index))
