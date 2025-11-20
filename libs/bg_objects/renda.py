import random
from libs.animation import Animation
from libs.texture import TextureWrapper

import pyray as ray

class Renda:

    @staticmethod
    def create(tex: TextureWrapper, index: int):
        map = [Renda0, Renda1, Renda2]
        selected_obj = map[index]
        return selected_obj(tex, index)

class BaseRenda:
    def __init__(self, tex: TextureWrapper, index: int):
        self.name = 'renda_' + str(index)
        self.hori_move = Animation.create_move(1500, total_distance=tex.screen_width)
        self.hori_move.start()

    def update(self, current_time_ms: float):
        self.hori_move.update(current_time_ms)

class Renda0(BaseRenda):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.vert_move = Animation.create_move(1500, total_distance=tex.screen_height + (80 * tex.screen_scale))
        self.vert_move.start()
        tex_list = tex.textures['renda'][self.name].texture
        num_of_rendas = len(tex_list) if isinstance(tex_list, list) else 0
        self.frame = random.randint(0, num_of_rendas - 1)
        self.x = random.randint(0, int(500 * tex.screen_scale))
        self.y = random.randint(0, int(20 * tex.screen_scale))

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.vert_move.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture('renda', self.name, frame=self.frame, x=self.hori_move.attribute+self.x, y=-self.vert_move.attribute+self.y)

class Renda1(BaseRenda):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.frame = random.randint(0, 5)
        self.y = random.randint(0, int(200 * tex.screen_scale))
        self.rotate = Animation.create_move(800, total_distance=tex.screen_height//2)
        self.rotate.start()
        self.origin = ray.Vector2(64, 64)

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.rotate.update(current_time_ms)
        if self.rotate.is_finished:
            self.rotate.restart()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture('renda', self.name, frame=self.frame, x=self.hori_move.attribute+self.origin.x, y=self.y+self.origin.y, origin=self.origin, rotation=self.rotate.attribute)

class Renda2(BaseRenda):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.vert_move = Animation.create_move(1500, total_distance=tex.screen_height + (80 * tex.screen_scale))
        self.vert_move.start()
        self.x = random.randint(0, int(500 * tex.screen_scale))
        self.y = random.randint(0, int(20 * tex.screen_scale))

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.vert_move.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture('renda', self.name, x=self.hori_move.attribute+self.x, y=-self.vert_move.attribute+self.y)

class RendaController:
    def __init__(self, tex: TextureWrapper, index: int, path: str ='background'):
        self.rendas = set()
        tex.load_zip(path, 'renda')
        self.tex = tex
        self.index = index
        self.path = path

    def add_renda(self):
        self.rendas.add(Renda.create(self.tex, self.index))

    def update(self, current_time_ms: float):
        remove = set()
        for renda in self.rendas:
            renda.update(current_time_ms)
            if renda.hori_move.is_finished:
                remove.add(renda)

        for renda in remove:
            self.rendas.remove(renda)

    def draw(self):
        for renda in self.rendas:
            renda.draw(self.tex)
