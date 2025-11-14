from libs.animation import Animation
from libs.bg_objects.fever import Fever3
from libs.bg_objects.bg_fever import BGFeverBase
from libs.bg_objects.bg_normal import BGNormalBase
from libs.bg_objects.chibi import ChibiController
from libs.bg_objects.dancer import BaseDancer, BaseDancerGroup
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
        self.bg_normal = BGNormalBase(self.tex_wrapper, 0, path)
        self.bg_fever = BGFever(self.tex_wrapper, 0, path)
        self.footer = Footer(self.tex_wrapper, 0, path)
        self.fever = Fever3(self.tex_wrapper, 0, bpm, path)
        self.dancer = DancerGroup(self.tex_wrapper, 0, bpm, self.max_dancers, path)
        self.renda = RendaController(self.tex_wrapper, 0, path)
        self.chibi = ChibiController(self.tex_wrapper, 0, bpm, path)

class DancerGroup(BaseDancerGroup):
    def __init__(self, tex: TextureWrapper, index: int, bpm: float, max_dancers: int, path: str):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip(path, f'dancer/{self.name}')
        self.spawn_positions = [2, 1, 3, 0, 4]
        self.active_dancers = [None] * max_dancers
        self.dancers = [BaseDancer(self.name, 0, bpm, tex),
                        BaseDancer(self.name, 1, bpm, tex),
                        BaseDancer(self.name, 1, bpm, tex),
                        BaseDancer(self.name, 1, bpm, tex),
                        BaseDancer(self.name, 1, bpm, tex)]
        self.add_dancer()

class DonBG(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: PlayerNum, path: str):
        super().__init__(tex, index, player_num, path)
        self.move = Animation.create_move(20000, total_distance=-1344)
        self.move.start()
        self.move.loop = True
    def _draw_textures(self, tex: TextureWrapper, fade: float, y: float):
        for i in range(16):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*168)+self.move.attribute, y=y)
            for j in range(3):
                tex.draw_texture(self.name, 'overlay', frame=self.is_clear, fade=fade, x=(i*168)+self.move.attribute, y=y+(j*70))

class BGFever(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int, path: str):
        super().__init__(tex, index, path)
        self.overlay_texture_change = Animation.create_texture_change(2049, textures=[(0, 683, 0), (683, 1366, 1), (1366, 2049, 2)])

    def start(self):
        self.overlay_texture_change.start()
        self.overlay_texture_change.loop = True
        self.transitioned = True

    def update(self, current_time_ms: float):
        self.overlay_texture_change.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'overlay', frame=self.overlay_texture_change.attribute)
