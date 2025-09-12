import random

from libs.animation import Animation
from libs.texture import TextureWrapper


class BGNormal:

    @staticmethod
    def create(tex: TextureWrapper, index: int):
        map = [BGNormal1, BGNormal2, BGNormal3, BGNormal4, BGNormal5]
        selected_obj = map[index]
        return selected_obj(tex, index)

class BGNormalBase:
    def __init__(self, tex: TextureWrapper, index: int):
        self.name = "bg_" + str(index)
        tex.load_zip('background', f'bg_normal/{self.name}')

class BGNormal1(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(9)
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'overlay', fade=self.flicker.attribute)

class BGNormal2(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(9)
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'overlay', fade=self.flicker.attribute)

class BGNormal3(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(10)
    def update(self, current_time_ms):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'center')
        tex.draw_texture(self.name, 'overlay')

        tex.draw_texture(self.name, 'lamps', index=0)
        tex.draw_texture(self.name, 'lamps', index=1, mirror='horizontal')

        tex.draw_texture(self.name, 'light_orange', index=0, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_orange', index=1, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_red', fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_green', fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_orange', index=2, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_yellow', index=0, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_yellow', index=1, fade=self.flicker.attribute)

        tex.draw_texture(self.name, 'side_l')
        tex.draw_texture(self.name, 'side_l_2')
        tex.draw_texture(self.name, 'side_r')

class BGNormal4(BGNormalBase):
    class Petal:
        def __init__(self):
            self.spawn_point = self.random_excluding_range()
            duration = random.randint(1400, 2000)
            self.move_x = Animation.create_move(duration, total_distance=random.randint(-300, 300))
            self.move_y = Animation.create_move(duration, total_distance=360)
            self.move_x.start()
            self.move_y.start()
        def random_excluding_range(self):
            while True:
                num = random.randint(0, 1280)
                if num < 260 or num > 540:
                    return num
        def update(self, current_time_ms):
            self.move_x.update(current_time_ms)
            self.move_y.update(current_time_ms)
        def draw(self, name: str, tex: TextureWrapper):
            tex.draw_texture(name, 'petal', x=self.spawn_point + self.move_x.attribute, y=360+self.move_y.attribute, fade=0.75)
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(11)
        self.turtle_move = tex.get_animation(12)
        self.turtle_change = tex.get_animation(13)
        self.petals = {self.Petal(), self.Petal(), self.Petal(), self.Petal(), self.Petal()}
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
        self.turtle_move.update(current_time_ms)
        self.turtle_change.update(current_time_ms)
        for petal in self.petals:
            petal.update(current_time_ms)
            if petal.move_y.is_finished:
                self.petals.remove(petal)
                self.petals.add(self.Petal())
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'chara')
        tex.draw_texture(self.name, 'turtle', frame=self.turtle_change.attribute, x=self.turtle_move.attribute)

        tex.draw_texture(self.name, 'overlay')

        for petal in self.petals:
            petal.draw(self.name, tex)

class BGNormal5(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(14)
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')

        for i in range(10):
            tex.draw_texture(self.name, 'paper_lamp', frame=9-i, index=i)

        for i in range(10):
            tex.draw_texture(self.name, 'light_overlay', index=i, fade=self.flicker.attribute)

        tex.draw_texture(self.name, 'overlay', fade=0.75)

        tex.draw_texture(self.name, 'lamp_overlay', index=0, fade=0.75)
        tex.draw_texture(self.name, 'lamp_overlay', index=1, fade=0.75)
        tex.draw_texture(self.name, 'lamp', index=0)
        tex.draw_texture(self.name, 'lamp', index=1)
