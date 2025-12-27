import random

from libs.animation import Animation
from libs.texture import TextureWrapper


class Dancer:

    @staticmethod
    def create(tex: TextureWrapper, index: int, bpm: float, max_dancers: int = 5, path: str = 'background'):
        map = [DancerGroup0, DancerGroup0, DancerGroup0, BaseDancerGroup, BaseDancerGroup, BaseDancerGroup,
                BaseDancerGroup, DancerGroupPoof1, DancerGroupPoof1, BaseDancerGroup, BaseDancerGroup, BaseDancerGroup,
                DancerGroupPoof2, DancerGroupPoof2, BaseDancerGroup, BaseDancerGroup, DancerGroupPoof2, BaseDancerGroup,
                BaseDancerGroup, BaseDancerGroup, BaseDancerGroup]
        selected_obj = map[index]
        return selected_obj(tex, index, bpm, max_dancers, path)

class BaseDancer:
    def __init__(self, name: str, index: int, bpm: float, tex: TextureWrapper):
        self.name = name
        self.index = index
        self.bpm = bpm
        self.tex = tex
        tex_list = tex.textures[self.name][str(self.index) + '_loop'].texture
        keyframe_len = tex_list if isinstance(tex_list, list) else [0]
        self.keyframes = [i for i in range(len(keyframe_len))]
        tex_list = tex.textures[self.name][str(self.index) + '_start'].texture
        s_keyframe_len = tex_list if isinstance(tex_list, list) else [0]
        self.start_keyframes = [i for i in range(len(s_keyframe_len))]
        self.is_started = False
        duration = (60000 / self.bpm) / 2
        self.total_duration = duration * len(self.keyframes)
        self.textures = [(duration*i, duration*(i+1), index) for i, index in enumerate(self.keyframes)]
        self.texture_change = Animation.create_texture_change(self.total_duration, textures=self.textures)
        self.texture_change.start()

    def start(self):
        self.is_started = True

        duration = (60000 / self.bpm)
        self.s_bounce_up = Animation.create_move(duration/2, start_position=-200 * self.tex.screen_scale, total_distance=350 * self.tex.screen_scale, ease_out='quadratic', delay=500)
        self.s_bounce_down = Animation.create_move(duration/2, total_distance=140 * self.tex.screen_scale, ease_in='quadratic', delay=self.s_bounce_up.duration + 500)
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

class Dancer0_4(BaseDancer):
    def __init__(self, name: str, index: int, bpm: float, tex: TextureWrapper):
        super().__init__(name, index, bpm, tex)
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
            tex.draw_texture(self.name, '4_start', frame=7, x=x, y=(-50 * self.tex.screen_scale)-self.s_bounce_up.attribute + self.s_bounce_down.attribute)
            tex.draw_texture(self.name, '4_start', frame=self.s_texture_change.attribute, x=x, y=-self.s_bounce_up.attribute + self.s_bounce_down.attribute)
        else:
            if 0 <= self.texture_change.attribute <= 3:
                tex.draw_texture(self.name, '4_loop', frame=54, x=x, y=-self.bounce_up.attribute + self.bounce_down.attribute)
            elif 5 <= self.texture_change.attribute <= 8:
                tex.draw_texture(self.name, '4_loop', frame=56, x=x, y=-self.bounce_up.attribute + self.bounce_down.attribute)
            elif self.texture_change.attribute == 4:
                tex.draw_texture(self.name, '4_loop', frame=55, x=x, y=-self.bounce_up.attribute + self.bounce_down.attribute)
            tex.draw_texture(self.name, '4_loop', frame=self.texture_change.attribute, x=x)

class DancerPoof(BaseDancer):
    def __init__(self, name: str, index: int, bpm: float, tex: TextureWrapper):
        super().__init__(name, index, bpm, tex)
        duration = (60000 / self.bpm)
        poof_keyframes = [((duration / 7)*i, (duration / 7)*(i+1), i) for i in range(7)]
        self.poof_texture_change = Animation.create_texture_change(duration, textures=poof_keyframes, delay=250)
        self.poof_texture_change.start()

    def update(self, current_time_ms: float, bpm: float):
        super().update(current_time_ms, bpm)
        self.poof_texture_change.update(current_time_ms)

    def draw(self, tex: TextureWrapper, x: int):
        super().draw(tex, x)
        if not self.poof_texture_change.is_finished:
            tex.draw_texture(self.name, 'poof', x=x, frame=self.poof_texture_change.attribute)

class DancerPoof2(DancerPoof):
    def draw(self, tex: TextureWrapper, x: int):
        if not self.is_started:
            return
        if not self.s_texture_change.is_finished:
            tex.draw_texture(self.name, str(self.index) + '_start', frame=self.s_texture_change.attribute, x=x, y=-self.s_bounce_up.attribute + self.s_bounce_down.attribute)
        else:
            tex.draw_texture(self.name, str(self.index) + '_loop', frame=self.texture_change.attribute, x=x)
        if not self.poof_texture_change.is_finished:
            tex.draw_texture(self.name, str(self.index) + '_poof', x=x, frame=self.poof_texture_change.attribute)

class BaseDancerGroup():
    def __init__(self, tex: TextureWrapper, index: int, bpm: float, max_dancers: int, path: str):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip(path, f'dancer/{self.name}')
        # center (2), left (1), right (3), far left (0), far right (4)
        all_positions = [2, 1, 3, 0, 4]
        self.spawn_positions = [pos for pos in all_positions if pos < max_dancers]
        self.active_dancers = [None] * max_dancers
        dancer_classes = [BaseDancer]
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
        total_width = tex.screen_width
        num_dancers = len(self.active_dancers)

        first_dancer = next((dancer for dancer in self.active_dancers if dancer is not None), None)
        if first_dancer is None:
            return
        dancer_width = tex.textures[self.name][str(first_dancer.index) + '_loop'].width

        available_space = total_width - (num_dancers * dancer_width)
        spacing = available_space / (num_dancers + 1)

        for i, dancer in enumerate(self.active_dancers):
            if dancer is not None:
                x_pos = int(spacing + i * (dancer_width + spacing))
                dancer.draw(tex, x_pos)

class DancerGroup0(BaseDancerGroup):
    def __init__(self, tex: TextureWrapper, index: int, bpm: float, max_dancers: int, path: str):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip(path, f'dancer/{self.name}')
        # center (2), left (1), right (3), far left (0), far right (4)
        self.spawn_positions = [2, 1, 3, 0, 4]
        self.active_dancers = [None] * max_dancers
        self.dancers = [BaseDancer(self.name, 0, bpm, tex), BaseDancer(self.name, 1, bpm, tex),
                       BaseDancer(self.name, 2, bpm, tex), BaseDancer(self.name, 3, bpm, tex),
                       Dancer0_4(self.name, 4, bpm, tex)]
        random.shuffle(self.dancers)
        self.add_dancer()

class DancerGroupPoof1(BaseDancerGroup):
    def __init__(self, tex: TextureWrapper, index: int, bpm: float, max_dancers: int, path: str):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip(path, f'dancer/{self.name}')
        # center (2), left (1), right (3), far left (0), far right (4)
        self.spawn_positions = [2, 1, 3, 0, 4]
        self.active_dancers = [None] * max_dancers
        dancer_classes = [DancerPoof]
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

class DancerGroupPoof2(BaseDancerGroup):
    def __init__(self, tex: TextureWrapper, index: int, bpm: float, max_dancers: int, path: str):
        self.name = 'dancer_' + str(index)
        self.active_count = 0
        tex.load_zip(path, f'dancer/{self.name}')
        # center (2), left (1), right (3), far left (0), far right (4)
        self.spawn_positions = [2, 1, 3, 0, 4]
        self.active_dancers = [None] * max_dancers
        dancer_classes = [DancerPoof2]
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
