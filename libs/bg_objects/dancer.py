import random

from libs.animation import Animation
from libs.texture import TextureWrapper

class Dancer:

    @staticmethod
    def create(tex: TextureWrapper, index: int, bpm: float):
        map = [DancerGroup0]
        selected_obj = map[index]
        return selected_obj(tex, index, bpm)

class BaseDancer:
    def __init__(self, name: str, index: int, bpm: float):
        self.name = name
        self.index = index
        self.bpm = bpm
        self.keyframes = []
        self.start_keyframes = []
        self.is_started = False

    def keyframe(self):
        duration = (60000 / self.bpm) / 2
        self.total_duration = duration * len(self.keyframes)
        self.textures = [(duration*i, duration*(i+1), index) for i, index in enumerate(self.keyframes)]
        self.texture_change = Animation.create_texture_change(self.total_duration, textures=self.textures)
        self.texture_change.start()

    def start(self):
        self.is_started = True

        duration = (60000 / self.bpm)
        self.s_bounce_up = Animation.create_move(duration/2, start_position=-200, total_distance=350, ease_out='quadratic', delay=500)
        self.s_bounce_down = Animation.create_move(duration/2, total_distance=140, ease_in='quadratic', delay=self.s_bounce_up.duration + 500)
        self.start_textures = [((duration / len(self.start_keyframes))*i, (duration / len(self.start_keyframes))*(i+1), index) for i, index in enumerate(self.start_keyframes)]
        self.s_texture_change = Animation.create_texture_change(duration, textures=self.start_textures, delay=500)
        self.s_texture_change.start()
        self.s_bounce_up.start()
        self.s_bounce_down.start()

    def update(self, current_time_ms: float, bpm: float):
        self.texture_change.update(current_time_ms)
        if self.is_started:
            self.s_texture_change.update(current_time_ms)
            self.s_bounce_up.update(current_time_ms)
            self.s_bounce_down.update(current_time_ms)
        if bpm != self.bpm:
            self.bpm = bpm
            duration = (60000 / bpm) / 2
            self.total_duration = duration * len(self.keyframes)
            self.textures = [(duration*i, duration*(i+1), index) for i, index in enumerate(self.keyframes)]
            self.texture_change.duration = self.total_duration
            self.texture_change.textures = self.textures
        if self.texture_change.is_finished:
            self.texture_change.restart()

    def draw(self, tex: TextureWrapper, x: int):
        if not self.is_started:
            return
        if not self.s_texture_change.is_finished:
            tex.draw_texture(self.name, str(self.index) + '_start', frame=self.s_texture_change.attribute, x=x, y=-self.s_bounce_up.attribute + self.s_bounce_down.attribute)
        else:
            tex.draw_texture(self.name, str(self.index) + '_loop', frame=self.texture_change.attribute, x=x)

class Dancer0_0(BaseDancer):
    def __init__(self, name: str, index: int, bpm: float):
        super().__init__(name, index, bpm)
        self.start_keyframes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4]
        self.keyframes = [0, 1, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 7, 8, 5, 9, 4, 10, 4, 9, 4, 10, 4, 9, 11, 12, 13, 12, 11, 12, 13, 12, 11, 9, 4, 10, 4, 9, 4, 10, 4, 9, 11, 12, 13, 12, 11, 12, 13, 12, 11]

class Dancer0_1(BaseDancer):
    def __init__(self, name: str, index: int, bpm: float):
        super().__init__(name, index, bpm)
        self.start_keyframes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4]
        self.keyframes = [0, 1, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 7, 8, 5, 9, 4, 10, 4, 9, 4, 10, 4, 9, 11, 12, 13, 12, 11, 12, 13, 12, 11, 9, 4, 10, 4, 9, 4, 10, 4, 9, 11, 12, 13, 12, 11, 12, 13, 12, 11]

class Dancer0_2(BaseDancer):
    def __init__(self, name: str, index: int, bpm: float):
        super().__init__(name, index, bpm)
        self.start_keyframes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2]
        self.keyframes = [0, 1, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 7, 8, 5, 9, 10, 11, 10, 9, 10, 11, 10, 9, 12, 13, 14, 13, 12, 13, 14, 13, 12, 9, 10, 11, 10, 9, 10, 11, 10, 9, 12, 13, 14, 13, 12, 13, 14, 13, 12]

class Dancer0_3(BaseDancer):
    def __init__(self, name: str, index: int, bpm: float):
        super().__init__(name, index, bpm)
        self.start_keyframes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2]
        self.keyframes = [0, 1, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 7, 8, 5, 9, 10, 11, 10, 9, 10, 11, 10, 9, 12, 13, 14, 13, 12, 13, 14, 13, 12, 9, 10, 11, 10, 9, 10, 11, 10, 9, 12, 13, 14, 13, 12, 13, 14, 13, 12]

class Dancer0_4(BaseDancer):
    def __init__(self, name: str, index: int, bpm: float):
        super().__init__(name, index, bpm)
        self.keyframes = [0, 1, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 7, 8, 5, 9, 10, 11, 10, 9, 10, 11, 10, 9, 12, 13, 14, 13, 12, 13, 14, 13, 12, 9, 10, 11, 10, 9, 10, 11, 10, 9, 12, 13, 14, 13, 12, 13, 14, 13, 12]
        self.start_keyframes = [0, 0, 0, 0, 1, 2, 2, 3, 4, 4, 5, 5, 5, 6, 6]
        duration = (60000 / bpm) / 2
        self.bounce_up = Animation.create_move(duration, total_distance=20, ease_out='quadratic', delay=duration*2)
        self.bounce_down = Animation.create_move(duration, total_distance=20, ease_in='quadratic', delay=duration*2+self.bounce_up.duration)
        self.bounce_up.start()
        self.bounce_down.start()

    def update(self, current_time_ms: float, bpm: float):
        super().update(current_time_ms, bpm)
        self.bounce_up.update(current_time_ms)
        self.bounce_down.update(current_time_ms)
        if self.bounce_down.is_finished:
            self.bounce_up.restart()
            self.bounce_down.restart()

    def draw(self, tex: TextureWrapper, x: int):
        if not self.is_started:
            return
        if not self.s_texture_change.is_finished:
            tex.draw_texture(self.name, '4_start', frame=7, x=x, y=-50-self.s_bounce_up.attribute + self.s_bounce_down.attribute)
            tex.draw_texture(self.name, '4_start', frame=self.s_texture_change.attribute, x=x, y=-self.s_bounce_up.attribute + self.s_bounce_down.attribute)
        else:
            if 0 <= self.texture_change.attribute <= 3:
                tex.draw_texture(self.name, '4_loop', frame=15, x=x, y=-self.bounce_up.attribute + self.bounce_down.attribute)
            elif 5 <= self.texture_change.attribute <= 8:
                tex.draw_texture(self.name, '4_loop', frame=17, x=x, y=-self.bounce_up.attribute + self.bounce_down.attribute)
            elif self.texture_change.attribute == 4:
                tex.draw_texture(self.name, '4_loop', frame=16, x=x, y=-self.bounce_up.attribute + self.bounce_down.attribute)
            tex.draw_texture(self.name, '4_loop', frame=self.texture_change.attribute, x=x)


class BaseDancerGroup():
    def __init__(self, tex: TextureWrapper, index: int, bpm: float):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip('background', f'dancer/{self.name}')
        self.dancers = []
        # Define spawn positions: center (2), left (1), right (3), far left (0), far right (4)
        self.spawn_positions = [2, 1, 3, 0, 4]
        self.active_dancers = [None] * 5

    def add_dancer(self):
        if self.active_count < len(self.dancers) and self.active_count < len(self.spawn_positions):
            position = self.spawn_positions[self.active_count]
            dancer = self.dancers[self.active_count]
            self.active_dancers[position] = dancer
            dancer.start()
            self.active_count += 1

    def update(self, current_time_ms: float, bpm: float):
        for dancer in self.dancers:
            dancer.update(current_time_ms, bpm)

    def draw(self, tex: TextureWrapper):
        for i, dancer in enumerate(self.active_dancers):
            if dancer is not None:
                dancer.draw(tex, 100 + i * 210)

class DancerGroup0(BaseDancerGroup):
    def __init__(self, tex: TextureWrapper, index: int, bpm: float):
        super().__init__(tex, index, bpm)
        self.dancers = [Dancer0_0(self.name, 0, bpm), Dancer0_1(self.name, 1, bpm),
                       Dancer0_2(self.name, 2, bpm), Dancer0_3(self.name, 3, bpm),
                       Dancer0_4(self.name, 4, bpm)]
        random.shuffle(self.dancers)
        for dancer in self.dancers:
            dancer.keyframe()
        self.add_dancer()
