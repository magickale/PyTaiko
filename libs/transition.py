import pyray as ray

from libs.utils import OutlinedText, global_tex


class Transition:
    """Transition class for the game."""
    def __init__(self, title: str, subtitle: str, is_second: bool = False) -> None:
        """Initialize the transition object.
        title: str - The title of the chart.
        subtitle: str - The subtitle of the chart.
        is_second: bool - Whether this is the second half of the transition."""
        self.is_finished = False
        self.rainbow_up = global_tex.get_animation(0)
        self.mini_up = global_tex.get_animation(1)
        self.chara_down = global_tex.get_animation(2)
        self.song_info_fade = global_tex.get_animation(3)
        self.song_info_fade_out = global_tex.get_animation(4)
        self.title = OutlinedText(title, 40, ray.WHITE)
        self.subtitle = OutlinedText(subtitle, 30, ray.WHITE)
        self.is_second = is_second

    def start(self):
        """Start the transition effect."""
        self.rainbow_up.start()
        self.mini_up.start()
        self.chara_down.start()
        self.song_info_fade.start()
        self.song_info_fade_out.start()

    def update(self, current_time_ms: float):
        """Update the transition effect."""
        self.rainbow_up.update(current_time_ms)
        self.chara_down.update(current_time_ms)
        self.mini_up.update(current_time_ms)
        self.song_info_fade.update(current_time_ms)
        self.song_info_fade_out.update(current_time_ms)
        self.is_finished = self.song_info_fade.is_finished

    def _draw_song_info(self):
        color_1 = ray.fade(ray.WHITE, self.song_info_fade.attribute)
        color_2 = ray.fade(ray.WHITE, min(0.70, self.song_info_fade.attribute))
        offset = 0
        if self.is_second:
            color_1 = ray.fade(ray.WHITE, self.song_info_fade_out.attribute)
            color_2 = ray.fade(ray.WHITE, min(0.70, self.song_info_fade_out.attribute))
            offset = 816 - self.rainbow_up.attribute
        global_tex.draw_texture('rainbow_transition', 'text_bg', y=-self.rainbow_up.attribute - offset, color=color_2)

        texture = self.title.texture
        x = 1280//2 - texture.width//2
        y = 1176 - texture.height//2 - int(self.rainbow_up.attribute) - offset - 20
        self.title.draw(outline_color=ray.BLACK, x=x, y=y, color=color_1)

        texture = self.subtitle.texture
        x = 1280//2 - texture.width//2
        self.subtitle.draw(outline_color=ray.BLACK, x=x, y=y + 50, color=color_1)

    def draw(self):
        """Draw the transition effect."""
        total_offset = 0
        if self.is_second:
            total_offset = 816
        global_tex.draw_texture('rainbow_transition', 'rainbow_bg_bottom', y=-self.rainbow_up.attribute - total_offset)
        global_tex.draw_texture('rainbow_transition', 'rainbow_bg_top', y=-self.rainbow_up.attribute - total_offset)
        global_tex.draw_texture('rainbow_transition', 'rainbow_bg', y=-self.rainbow_up.attribute - total_offset)
        offset = self.chara_down.attribute
        chara_offset = 0
        if self.is_second:
            offset = self.chara_down.attribute - self.mini_up.attribute//3
            chara_offset = 408
        global_tex.draw_texture('rainbow_transition', 'chara_left', x=-self.mini_up.attribute//2 - chara_offset, y=-self.mini_up.attribute + offset - total_offset)
        global_tex.draw_texture('rainbow_transition', 'chara_right', x=self.mini_up.attribute//2 + chara_offset, y=-self.mini_up.attribute + offset - total_offset)
        global_tex.draw_texture('rainbow_transition', 'chara_center', y=-self.rainbow_up.attribute + offset - total_offset)

        self._draw_song_info()
