import pyray as ray

from libs.animation import Animation
from libs.utils import OutlinedText, global_data


class Transition:
    def __init__(self, title: str, subtitle: str) -> None:
        self.is_finished = False
        self.rainbow_up = global_data.tex.get_animation(0)
        self.mini_up = global_data.tex.get_animation(1)
        self.chara_down = global_data.tex.get_animation(2)
        self.song_info_fade = global_data.tex.get_animation(3)
        self.song_info_fade_out = global_data.tex.get_animation(4)
        self.title = OutlinedText(title, 40, ray.WHITE, ray.BLACK, outline_thickness=5)
        self.subtitle = OutlinedText(subtitle, 30, ray.WHITE, ray.BLACK, outline_thickness=5)
        self.is_second = False

    def start(self):
        self.rainbow_up.start()
        self.mini_up.start()
        self.chara_down.start()
        self.song_info_fade.start()
        self.song_info_fade_out.start()

    def update(self, current_time_ms: float):
        self.rainbow_up.update(current_time_ms)
        self.chara_down.update(current_time_ms)
        self.mini_up.update(current_time_ms)
        self.song_info_fade.update(current_time_ms)
        self.song_info_fade_out.update(current_time_ms)
        self.is_finished = self.song_info_fade.is_finished

    def draw_song_info(self):
        color_1 = ray.fade(ray.WHITE, self.song_info_fade.attribute)
        color_2 = ray.fade(ray.WHITE, min(0.70, self.song_info_fade.attribute))
        offset = 0
        if self.is_second:
            color_1 = ray.fade(ray.WHITE, self.song_info_fade_out.attribute)
            color_2 = ray.fade(ray.WHITE, min(0.70, self.song_info_fade_out.attribute))
            offset = 816 - self.rainbow_up.attribute
        global_data.tex.draw_texture('rainbow_transition', 'text_bg', y=-self.rainbow_up.attribute - offset, color=color_2)

        texture = self.title.texture
        y = 1176 - texture.height//2 - int(self.rainbow_up.attribute) - offset
        dest = ray.Rectangle(1280//2 - texture.width//2, y - 20, texture.width, texture.height)
        self.title.draw(self.title.default_src, dest, ray.Vector2(0, 0), 0, color_1)

        texture = self.subtitle.texture
        dest = ray.Rectangle(1280//2 - texture.width//2, y + 30, texture.width, texture.height)
        self.subtitle.draw(self.subtitle.default_src, dest, ray.Vector2(0, 0), 0, color_1)

    def draw(self):
        total_offset = 0
        if self.is_second:
            total_offset = 816
        global_data.tex.draw_texture('rainbow_transition', 'rainbow_bg_bottom', y=-self.rainbow_up.attribute - total_offset)
        global_data.tex.draw_texture('rainbow_transition', 'rainbow_bg_top', y=-self.rainbow_up.attribute - total_offset)
        global_data.tex.draw_texture('rainbow_transition', 'rainbow_bg', y=-self.rainbow_up.attribute - total_offset)
        offset = self.chara_down.attribute
        chara_offset = 0
        if self.is_second:
            offset = self.chara_down.attribute - self.mini_up.attribute//3
            chara_offset = 408
        global_data.tex.draw_texture('rainbow_transition', 'chara_left', x=-self.mini_up.attribute//2 - chara_offset, y=-self.mini_up.attribute + offset - total_offset)
        global_data.tex.draw_texture('rainbow_transition', 'chara_right', x=self.mini_up.attribute//2 + chara_offset, y=-self.mini_up.attribute + offset - total_offset)
        global_data.tex.draw_texture('rainbow_transition', 'chara_center', y=-self.rainbow_up.attribute + offset - total_offset)

        self.draw_song_info()

class Transition2:
    def __init__(self, screen_height: int, title: str, subtitle: str) -> None:
        duration = 266
        self.is_finished = False
        self.rainbow_up = Animation.create_move(duration, start_position=0, total_distance=screen_height + global_data.textures['scene_change_rainbow'][2].height, ease_in='cubic')
        self.rainbow_up.start()
        self.chara_down = None
        self.title = OutlinedText(title, 40, ray.WHITE, ray.BLACK, outline_thickness=5)
        self.subtitle = OutlinedText(subtitle, 30, ray.WHITE, ray.BLACK, outline_thickness=5)
        self.song_info_fade = Animation.create_fade(duration/2)
        self.song_info_fade.start()
    def update(self, current_time_ms: float):
        self.rainbow_up.update(current_time_ms)
        self.song_info_fade.update(current_time_ms)
        if self.rainbow_up.is_finished and self.chara_down is None:
            self.chara_down = Animation.create_move(33, start_position=0, total_distance=30)
            self.chara_down.start()

        if self.chara_down is not None:
            self.chara_down.update(current_time_ms)
            self.is_finished = self.chara_down.is_finished

    def draw_song_info(self):
        texture = global_data.textures['scene_change_rainbow'][6]
        y = 720//2 - texture.height
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(1280//2 - (texture.width*3)//2, y, texture.width*3, texture.height*2)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, min(0.70, self.song_info_fade.attribute)))

        texture = self.title.texture
        y = 720//2 - texture.height//2 - 20
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(1280//2 - texture.width//2, y, texture.width, texture.height)
        self.title.draw(src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, self.song_info_fade.attribute))

        texture = self.subtitle.texture
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(1280//2 - texture.width//2, y + 50, texture.width, texture.height)
        self.subtitle.draw(src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, self.song_info_fade.attribute))

    def draw(self, screen_height: int):
        ray.draw_texture(global_data.textures['scene_change_rainbow'][1], 0, screen_height - int(self.rainbow_up.attribute), ray.WHITE)
        texture = global_data.textures['scene_change_rainbow'][0]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(0, -int(self.rainbow_up.attribute), texture.width, screen_height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)
        texture = global_data.textures['scene_change_rainbow'][3]
        offset = 0
        if self.chara_down is not None:
            offset = int(self.chara_down.attribute)
        ray.draw_texture(global_data.textures['scene_change_rainbow'][4], 142, 14 -int(self.rainbow_up.attribute*3) - offset, ray.WHITE)
        ray.draw_texture(global_data.textures['scene_change_rainbow'][5], 958, 144 -int(self.rainbow_up.attribute*3) - offset, ray.WHITE)
        ray.draw_texture(texture, 76, -int(self.rainbow_up.attribute*3) - offset, ray.WHITE)

        self.draw_song_info()
