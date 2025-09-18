from enum import Enum
import pyray as ray

from libs.utils import OutlinedText, global_tex


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

        dest = ray.Rectangle(x+136 - (self.name.texture.width//2) + offset, y+24, self.name.texture.width, self.name.texture.height)
        self.name.draw(self.name.default_src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, fade))
        dest = ray.Rectangle(x+136 - (self.title.texture.width//2) + title_offset, y-3, self.title.texture.width, self.title.texture.height)
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
