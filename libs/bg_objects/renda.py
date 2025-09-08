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
        tex.load_zip('background', 'renda')
        self.hori_move = Animation.create_move(1500, total_distance=1280)
        self.hori_move.start()

    def update(self, current_time_ms: float):
        self.hori_move.update(current_time_ms)

class Renda0(BaseRenda):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.vert_move = Animation.create_move(1500, total_distance=800)
        self.vert_move.start()
        self.frame = random.randint(0, 5)
        self.x = random.randint(0, 500)
        self.y = random.randint(0, 20)

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.vert_move.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture('renda', self.name, frame=self.frame, x=self.hori_move.attribute+self.x, y=-self.vert_move.attribute+self.y)

class Renda1(BaseRenda):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.frame = random.randint(0, 5)
        self.y = random.randint(0, 200)
        self.rotate = Animation.create_move(800, total_distance=360)
        self.rotate.start()

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.rotate.update(current_time_ms)
        if self.rotate.is_finished:
            self.rotate.restart()

    def draw(self, tex: TextureWrapper):
        origin = ray.Vector2(64, 64)
        tex.draw_texture('renda', self.name, frame=self.frame, x=self.hori_move.attribute+origin.x, y=self.y+origin.y, origin=origin, rotation=self.rotate.attribute)

class Renda2(BaseRenda):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.vert_move = Animation.create_move(1500, total_distance=800)
        self.vert_move.start()
        self.x = random.randint(0, 500)
        self.y = random.randint(0, 20)

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.vert_move.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture('renda', self.name, x=self.hori_move.attribute+self.x, y=-self.vert_move.attribute+self.y)

class RendaController:
    def __init__(self, tex: TextureWrapper, index: int):
        self.rendas = set()
        self.tex = tex
        self.index = index

    def add_renda(self):
        self.rendas.add(Renda.create(self.tex, self.index))

    def update(self, current_time_ms: int):
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
