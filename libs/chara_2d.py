from libs.animation import Animation
from libs.utils import global_tex

class Chara2D:
    def __init__(self, index: int, bpm: float, path: str = 'chara'):
        self.name = "chara_" + str(index)
        self.tex = global_tex
        self.anims = dict()
        self.bpm = bpm
        self.current_anim = 'normal'
        self.past_anim = 'normal'
        self.is_rainbow = False
        self.is_clear = False
        self.temp_anims = {'10_combo','10_combo_max', 'soul_in', 'clear_in', 'balloon_pop', 'balloon_miss'}
        for name in self.tex.textures[self.name]:
            tex_list = self.tex.textures[self.name][name].texture
            keyframe_len = len(tex_list) if isinstance(tex_list, list) else 1
            if index == 0:
                duration = 2250*2 / self.bpm
            else:
                duration = 2250 / self.bpm
            total_duration = duration * keyframe_len
            keyframes = [i for i in range(keyframe_len)]
            textures = [[duration*i, duration*(i+1), index] for i, index in enumerate(keyframes)]
            self.anims[name] = Animation.create_texture_change(total_duration, textures=textures)
            self.anims[name].start()

    def set_animation(self, name: str):
        if name == self.current_anim:
            return
        if self.current_anim in self.temp_anims:
            return
        self.past_anim = self.current_anim
        if name == 'balloon_pop' or name == 'balloon_miss':
            self.past_anim = 'normal'
            if self.is_clear:
                self.past_anim = 'clear'
        self.current_anim = name
        self.anims[name].start()
    def update(self, current_time_ms: float, bpm: float, is_clear: bool, is_rainbow: bool):
        if is_rainbow and not self.is_rainbow:
            self.is_rainbow = True
            self.set_animation('soul_in')
        if is_clear and not self.is_clear:
            self.is_clear = True
            self.set_animation('clear_in')
            self.past_anim = 'clear'
        if bpm != self.bpm:
            self.bpm = bpm
            for name in self.tex.textures[self.name]:
                tex_list = self.tex.textures[self.name][name].texture
                keyframe_len = len(tex_list) if isinstance(tex_list, list) else 1
                duration = 2250 / self.bpm
                total_duration = duration * keyframe_len
                keyframes = [i for i in range(keyframe_len)]
                textures = [[duration*i, duration*(i+1), index] for i, index in enumerate(keyframes)]
                self.anims[name] = Animation.create_texture_change(total_duration, textures=textures)
                self.anims[name].start()
        self.anims[self.current_anim] = self.anims[self.current_anim]
        self.anims[self.current_anim].update(current_time_ms)
        if self.anims[self.current_anim].is_finished:
            if self.current_anim in self.temp_anims:
                self.anims[self.current_anim].reset()
                self.current_anim = self.past_anim
            self.anims[self.current_anim].restart()

    def draw(self, x: float = 0, y: float = 0, mirror=False):
        if self.is_rainbow and self.current_anim not in {'soul_in', 'balloon_pop', 'balloon_popping'}:
            self.tex.draw_texture(self.name, self.current_anim + '_max', frame=self.anims[self.current_anim].attribute, x=x, y=y)
        else:
            if mirror:
                self.tex.draw_texture(self.name, self.current_anim, frame=self.anims[self.current_anim].attribute, x=x, y=y, mirror='horizontal')
            else:
                self.tex.draw_texture(self.name, self.current_anim, frame=self.anims[self.current_anim].attribute, x=x, y=y)
