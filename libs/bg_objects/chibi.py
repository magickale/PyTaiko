import random
from libs.animation import Animation, get_current_ms
from libs.texture import TextureWrapper

import pyray as ray

class Chibi:

    @staticmethod
    def create(index: int, bpm: float, bad: bool):
        if bad:
            return ChibiBad(index, bpm)
        map = [Chibi0, Chibi1, Chibi2, Chibi3, Chibi4, Chibi5, Chibi6,
        Chibi7, Chibi8, Chibi9, Chibi10, Chibi11, Chibi12, Chibi13]
        selected_obj = map[index]
        return selected_obj(index, bpm)

class BaseChibi:
    def __init__(self, index: int, bpm: float):
        self.name = 'chibi_' + str(index)
        self.bpm = bpm
        self.hori_move = Animation.create_move(60000 / self.bpm * 5, total_distance=1280)
        self.hori_move.start()
        self.vert_move = Animation.create_move(60000 / self.bpm / 2, total_distance=50, reverse_delay=0)
        self.vert_move.start()
        self.keyframes = [0]

    def keyframe(self):
        duration = (60000 / self.bpm) / 2
        textures = [((duration / len(self.keyframes))*i, (duration / len(self.keyframes))*(i+1), index) for i, index in enumerate(self.keyframes)]
        self.texture_change = Animation.create_texture_change(duration, textures=textures)
        self.texture_change.start()

    def update(self, current_time_ms: float):
        self.hori_move.update(current_time_ms)
        self.vert_move.update(current_time_ms)
        if self.vert_move.is_finished:
            self.vert_move.restart()
        self.texture_change.update(current_time_ms)
        if self.texture_change.is_finished:
            self.texture_change.restart()

class ChibiBad(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 2)
        self.keyframes = [3, 4]
        duration = (60000 / self.bpm) / 2
        self.fade_in = Animation.create_fade(duration, initial_opacity=0.0, final_opacity=1.0)
        self.fade_in.start()
        s_keyframes = [0, 1, 2]
        textures = [((duration / len(s_keyframes))*i, (duration / len(s_keyframes))*(i+1), index) for i, index in enumerate(s_keyframes)]
        self.s_texture_change = Animation.create_texture_change(duration, textures=textures)
        self.s_texture_change.start()
        duration *= 2
        textures = [((duration / len(self.keyframes))*i, (duration / len(self.keyframes))*(i+1), index) for i, index in enumerate(self.keyframes)]
        self.texture_change = Animation.create_texture_change(duration, textures=textures)
        self.texture_change.start()

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.s_texture_change.update(current_time_ms)
        self.fade_in.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        if not self.s_texture_change.is_finished:
            tex.draw_texture('chibi_bad', '0', frame=self.s_texture_change.attribute, x=self.hori_move.attribute, y=self.vert_move.attribute, fade=self.fade_in.attribute)
        else:
            tex.draw_texture('chibi_bad', '0', frame=self.texture_change.attribute, x=self.hori_move.attribute, y=self.vert_move.attribute)

class Chibi0(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 2)
        self.keyframes = [0, 1, 2, 3, 2, 1]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=self.vert_move.attribute)

class Chibi1(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [0, 1, 2, 3, 4, 3, 2, 1]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi2(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.rotate = Animation.create_move(60000 / self.bpm / 2, total_distance=360, reverse_delay=0)
        self.rotate.start()
        self.keyframe()

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.rotate.update(current_time_ms)
        if self.rotate.is_finished:
            self.rotate.restart()

    def draw(self, tex: TextureWrapper):
        origin = ray.Vector2(64, 64)
        tex.draw_texture(self.name, str(self.index), x=self.hori_move.attribute+origin.x, y=origin.y, origin=origin, rotation=self.rotate.attribute)

class Chibi3(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(8)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi4(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(7)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute)

class Chibi5(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [0, 1, 2, 3, 4, 5, 6, 7, 6, 7, 6, 7, 8]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute)

class Chibi6(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(10)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi7(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(3) if self.index < 2]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi8(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(5)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute)

class Chibi9(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(7)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi10(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(7)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi11(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 1)
        self.keyframes = [i for i in range(10)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi12(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 1)
        self.keyframes = [i for i in range(6)]
        self.keyframe()

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, str(self.index), frame=self.texture_change.attribute, x=self.hori_move.attribute, y=-self.vert_move.attribute)

class Chibi13(BaseChibi):
    def __init__(self, index: int, bpm: float):
        super().__init__(index, bpm)
        self.index = random.randint(0, 3)
        self.keyframes = [i for i in range(7)]
        duration = (60000 / self.bpm)
        self.scale = Animation.create_fade(duration, initial_opacity=1.0, final_opacity=0.75, delay=duration, reverse_delay=duration)
        self.scale.start()
        self.frame = 0
        self.keyframe()

    def update(self, current_time_ms: float):
        super().update(current_time_ms)
        self.scale.update(current_time_ms)
        if self.scale.is_finished:
            self.scale.restart()
        if self.scale.attribute == 0.75:
            self.frame = 1
        else:
            self.frame = 0

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'tail', frame=self.frame, x=self.hori_move.attribute, y=-self.vert_move.attribute)
        if self.scale.attribute == 0.75:
            tex.draw_texture(self.name, str(self.index), frame=self.frame, x=self.hori_move.attribute, y=-self.vert_move.attribute)
        else:
            tex.draw_texture(self.name, str(self.index), scale=self.scale.attribute, center=True, frame=self.frame, x=self.hori_move.attribute, y=-self.vert_move.attribute)


class ChibiController:
    def __init__(self, tex: TextureWrapper, index: int, bpm: float):
        self.chibis = set()
        self.tex = tex
        self.index = index
        self.name = 'chibi_' + str(index)
        self.bpm = bpm
        tex.load_zip('background', f'chibi/{self.name}')
        tex.load_zip('background', f'chibi/chibi_bad')

    def add_chibi(self, bad=False):
        self.chibis.add(Chibi.create(self.index, self.bpm, bad))

    def update(self, current_time_ms: float, bpm: float):
        self.bpm = bpm
        remove = set()
        for chibi in self.chibis:
            chibi.update(current_time_ms)
            if chibi.hori_move.is_finished:
                remove.add(chibi)

        for chibi in remove:
            self.chibis.remove(chibi)

    def draw(self):
        for chibi in self.chibis:
            chibi.draw(self.tex)
