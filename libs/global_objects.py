from enum import Enum
import pyray as ray

from libs.utils import OutlinedText, get_config, global_tex
from libs.audio import audio


class Nameplate:
    def __init__(self, name: str, title: str, player_num: int, dan: int, is_gold: bool):
        self.name = OutlinedText(name, 22, ray.WHITE, ray.BLACK, outline_thickness=3.0)
        self.title = OutlinedText(title, 20, ray.BLACK, ray.WHITE, outline_thickness=0)
        self.dan_index = dan
        self.player_num = player_num
        self.is_gold = is_gold
    def update(self, current_time_ms: float):
        pass

    def unload(self):
        self.name.unload()
        self.title.unload()
    def draw(self, x: int, y: int, fade: float = 1.0):
        tex = global_tex
        tex.draw_texture('nameplate', 'shadow', x=x, y=y, fade=min(0.5, fade))
        if self.player_num == -1:
            frame = 2
            title_offset = 0
        else:
            frame = self.player_num-1
            title_offset = 14
        tex.draw_texture('nameplate', 'frame_top', frame=frame, x=x, y=y, fade=fade)
        tex.draw_texture('nameplate', 'outline', x=x, y=y, fade=fade)
        offset = 0
        if self.dan_index != -1:
            tex.draw_texture('nameplate', 'dan_emblem_bg', x=x, y=y, fade=fade)
            if self.is_gold:
                tex.draw_texture('nameplate', 'dan_emblem_gold', x=x, y=y, frame=self.dan_index, fade=fade)
            else:
                tex.draw_texture('nameplate', 'dan_emblem', x=x, y=y, frame=self.dan_index, fade=fade)
            offset = 34
        if self.player_num != -1:
            tex.draw_texture('nameplate', f'{self.player_num}p', x=x, y=y, fade=fade)

        dest = ray.Rectangle(x+136 - (min(255 - offset*4, self.name.texture.width)//2) + offset, y+24, min(255 - offset*4, self.name.texture.width), self.name.texture.height)
        self.name.draw(self.name.default_src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, fade))
        dest = ray.Rectangle(x+136 - (min(255 - offset*2, self.title.texture.width)//2) + title_offset, y-3, min(255 - offset*2, self.title.texture.width), self.title.texture.height)
        self.title.draw(self.title.default_src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, fade))

class Indicator:
    class State(Enum):
        SKIP = 0
        SIDE = 1
        SELECT = 2
        WAIT = 3
    def __init__(self, state: State):
        self.state = state
        self.don_fade = global_tex.get_animation(6)
        self.blue_arrow_move = global_tex.get_animation(7)
        self.blue_arrow_fade = global_tex.get_animation(8)

    def update(self, current_time_ms: float):
        self.don_fade.update(current_time_ms)
        self.blue_arrow_move.update(current_time_ms)
        self.blue_arrow_fade.update(current_time_ms)

    def draw(self, x: int, y: int, fade=1.0):
        tex = global_tex
        tex.draw_texture('indicator', 'background', x=x, y=y, fade=fade)
        tex.draw_texture('indicator', 'text', frame=self.state.value, x=x, y=y, fade=fade)
        tex.draw_texture('indicator', 'drum_face', index=self.state.value, x=x, y=y, fade=fade)
        if self.state == Indicator.State.SELECT:
            tex.draw_texture('indicator', 'drum_kat', fade=min(fade, self.don_fade.attribute), x=x, y=y)

            tex.draw_texture('indicator', 'drum_kat', fade=min(fade, self.don_fade.attribute), x=x+23, y=y, mirror='horizontal')
            tex.draw_texture('indicator', 'drum_face', x=x+175, y=y, fade=fade)

            tex.draw_texture('indicator', 'drum_don', fade=min(fade, self.don_fade.attribute), index=self.state.value, x=x+214, y=y)
            tex.draw_texture('indicator', 'blue_arrow', x=x-self.blue_arrow_move.attribute, y=y, fade=min(fade, self.blue_arrow_fade.attribute))
            tex.draw_texture('indicator', 'blue_arrow', index=1, x=x+self.blue_arrow_move.attribute, y=y, mirror='horizontal', fade=min(fade, self.blue_arrow_fade.attribute))
        else:
            tex.draw_texture('indicator', 'drum_don', fade=min(fade, self.don_fade.attribute), index=self.state.value, x=x, y=y)

class CoinOverlay:
    def __init__(self):
        pass
    def update(self, current_time_ms: float):
        pass
    def draw(self, x: int = 0, y: int = 0):
        tex = global_tex
        tex.draw_texture('overlay', 'free_play', x=x, y=y)

class AllNetIcon:
    def __init__(self):
        pass
    def update(self, current_time_ms: float):
        pass
    def draw(self, x: int = 0, y: int = 0):
        tex = global_tex
        tex.draw_texture('overlay', 'allnet_indicator', x=x, y=y, frame=0)

class EntryOverlay:
    def __init__(self):
        self.online = False
    def update(self, current_time_ms: float):
        pass
    def draw(self, x: int = 0, y: int = 0):
        tex = global_tex
        tex.draw_texture('overlay', 'banapass_or', x=x, y=y, frame=self.online)
        tex.draw_texture('overlay', 'banapass_card', x=x, y=y, frame=self.online)
        tex.draw_texture('overlay', 'banapass_osaifu_keitai', x=x, y=y, frame=self.online)
        if not self.online:
            tex.draw_texture('overlay', 'banapass_no', x=x, y=y, frame=self.online)

        tex.draw_texture('overlay', 'camera', x=x, y=y, frame=0)

class Timer:
    def __init__(self, time: int, current_time_ms: float, confirm_func):
        self.time = time
        self.last_time = current_time_ms
        self.counter = str(self.time)
        self.num_resize = global_tex.get_animation(9)
        self.highlight_resize = global_tex.get_animation(10)
        self.highlight_fade = global_tex.get_animation(11)
        self.confirm_func = confirm_func
        self.is_finished = False
        self.is_frozen = get_config()["general"]["timer_frozen"]
    def update(self, current_time_ms: float):
        if self.time == 0 and not self.is_finished and not audio.is_sound_playing('voice_timer_0'):
            self.is_finished = True
            self.confirm_func()
        self.num_resize.update(current_time_ms)
        self.highlight_resize.update(current_time_ms)
        self.highlight_fade.update(current_time_ms)
        if self.is_frozen:
            return
        if current_time_ms >= self.last_time + 1000 and self.time > 0:
            self.time -= 1
            self.last_time = current_time_ms
            self.counter = str(self.time)
            if self.time < 10:
                audio.play_sound('timer_blip')
                self.num_resize.start()
                self.highlight_fade.start()
                self.highlight_resize.start()
            if self.time == 10:
                audio.play_sound('voice_timer_10')
            elif self.time == 5:
                audio.play_sound('voice_timer_5')
            elif self.time == 0:
                audio.play_sound('voice_timer_0')
    def draw(self, x: int = 0, y: int = 0):
        tex = global_tex
        if self.time < 10:
            tex.draw_texture('timer', 'bg_red')
            counter_name = 'counter_white'
            tex.draw_texture('timer', 'highlight', fade=self.highlight_fade.attribute, scale=self.highlight_resize.attribute, center=True)
        else:
            tex.draw_texture('timer', 'bg')
            counter_name = 'counter_black'
        margin = 40
        total_width = len(self.counter) * margin
        for i, digit in enumerate(self.counter):
            tex.draw_texture('timer', counter_name, frame=int(digit), x=-(total_width//2)+(i*margin), scale=self.num_resize.attribute, center=True)
