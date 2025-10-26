import random
from libs.animation import Animation
from libs.bg_objects.bg_fever import BGFever4
from libs.bg_objects.bg_normal import BGNormal2
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.dancer import BaseDancer, BaseDancerGroup
from libs.bg_objects.don_bg import DonBGBase
from libs.bg_objects.renda import RendaController
from libs.texture import TextureWrapper

class Background:
    def __init__(self, tex: TextureWrapper, player_num: int, bpm: float, path: str, max_dancers: int):
        self.tex_wrapper = tex
        self.max_dancers = max_dancers
        self.don_bg = DonBG(self.tex_wrapper, 0, 1, path)
        self.bg_normal = BGNormal(self.tex_wrapper, 0, path)
        self.bg_fever = BGFever(self.tex_wrapper, 0, path)
        self.footer = None
        self.fever = None
        self.dancer = DancerGroup(self.tex_wrapper, 0, bpm, self.max_dancers, path)
        self.renda = RendaController(self.tex_wrapper, 0, path)
        self.chibi = ChibiController(self.tex_wrapper, 0, bpm, path)
        for _ in range(3):
            self.dancer.add_dancer()

class BGFever(BGFever4):
    def __init__(self, tex: TextureWrapper, index: int, path: str):
        super().__init__(tex, index, path)
        self.vertical_move = Animation.create_move(tex.animations[15].duration, total_distance=328)
        self.vertical_move.start()
        self.vertical_move.loop = True

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'overlay')
        for i in range(10):
            for j in range(2):
                tex.draw_texture(self.name, 'petals', x=(i * 328)-self.horizontal_move.attribute, y=(j * 328) + self.vertical_move.attribute)

class DancerGroup(BaseDancerGroup):
    def __init__(self, tex: TextureWrapper, index: int, bpm: float, max_dancers: int, path: str):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip(path, f'dancer/{self.name}')
        # center (2), left (1), right (3), far left (0), far right (4)
        self.spawn_positions = [2, 1, 3, 0, 4]
        self.active_dancers = [None] * max_dancers
        dancer_classes = [Dancer]
        tex_set = set()
        tex_dict = tex.textures['dancer_' + str(index)]
        for key in tex_dict.keys():
            if key[0].isdigit():
                tex_set.add(int(key[0]))
        self.dancers = []
        for i in range(max_dancers):
            DancerClass = random.choice(dancer_classes)
            dancer = DancerClass(self.name, i % len(tex_set), bpm, tex)
            self.dancers.append(dancer)

        random.shuffle(self.dancers)
        self.add_dancer()

class Dancer(BaseDancer):
    def draw(self, tex: TextureWrapper, x: int):
        super().draw(tex, x)
        tex.draw_texture(self.name, 'shadow', x=x, fade=0.50)

class BGNormal(BGNormal2):
    def draw(self, tex: TextureWrapper):
        super().draw(tex)
        tex.draw_texture(self.name, 'curtain')

class DonBG(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: int, path: str):
        super().__init__(tex, index, player_num, path)
        self.move = Animation.create_move(10000, total_distance=-1280)
        self.move.start()
        self.move.loop = True
    def draw(self, tex: TextureWrapper):
        self._draw_textures(tex, 1.0)
        if self.is_clear:
            self._draw_textures(tex, self.clear_fade.attribute)
    def _draw_textures(self, tex: TextureWrapper, fade: float):
        for i in range(2):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*1280)+self.move.attribute)
