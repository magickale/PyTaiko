from libs.animation import Animation
from libs.texture import TextureWrapper

class Fever:

    @staticmethod
    def create(tex: TextureWrapper, index: int, bpm: float):
        map = [Fever0, Fever1, Fever2, Fever3]
        selected_obj = map[index]
        return selected_obj(tex, index, bpm)

class BaseFever:
    def __init__(self, tex: TextureWrapper, index: int, bpm: float):
        self.name = 'fever_' + str(index)
        tex.load_zip('background', f'fever/{self.name}')
        self.bounce_up = Animation.create_move((60000 / bpm) / 2, total_distance=50, ease_out='quadratic')
        self.bounce_down = Animation.create_move((60000 / bpm) / 2, total_distance=50, ease_in='quadratic', delay=self.bounce_up.duration)

    def start(self):
        self.bounce_down.start()
        self.bounce_up.start()

    def update(self, current_time_ms: int, bpm: float):
        self.bounce_up.update(current_time_ms)
        self.bounce_down.update(current_time_ms)
        if self.bounce_down.is_finished:
            self.bounce_up.duration = (60000 / bpm) / 2
            self.bounce_down.duration = (60000 / bpm) / 2
            self.bounce_up.restart()
            self.bounce_down.restart()

class Fever0(BaseFever):
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'overlay_l', y=self.bounce_down.attribute-self.bounce_up.attribute)
        tex.draw_texture(self.name, 'overlay_r', y=self.bounce_down.attribute-self.bounce_up.attribute)

class Fever1(BaseFever):
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'overlay_l', y=self.bounce_down.attribute-self.bounce_up.attribute)
        tex.draw_texture(self.name, 'overlay_r', y=self.bounce_down.attribute-self.bounce_up.attribute)

class Fever2(BaseFever):
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'overlay_l', y=self.bounce_down.attribute-self.bounce_up.attribute)
        tex.draw_texture(self.name, 'overlay_r', y=self.bounce_down.attribute-self.bounce_up.attribute)

class Fever3(BaseFever):
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'overlay', y=self.bounce_down.attribute-self.bounce_up.attribute)
