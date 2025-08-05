import random
from pathlib import Path

import pyray as ray

from libs.audio import audio
from libs.texture import tex
from libs.utils import (
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_r_don_pressed,
)
from libs.video import VideoPlayer


class State:
    OP_VIDEO = 0
    WARNING = 1
    ATTRACT_VIDEO = 2

class TitleScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        video_dir = Path(global_data.config["paths"]["video_path"]) / "op_videos"
        self.op_video_list = [file for file in video_dir.glob("**/*.mp4")]
        video_dir = Path(global_data.config["paths"]["video_path"]) / "attract_videos"
        self.attract_video_list = [file for file in video_dir.glob("**/*.mp4")]
        self.screen_init = False

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        title_dir = sounds_dir / "title"
        self.sound_don = audio.load_sound(sounds_dir / "inst_00_don.wav")
        self.sound_bachi_swipe = audio.load_sound(title_dir / "SE_ATTRACT_2.ogg")
        self.sound_bachi_hit = audio.load_sound(title_dir / "SE_ATTRACT_3.ogg")
        self.sound_warning_message = audio.load_sound(title_dir / "VO_ATTRACT_3.ogg")
        self.sound_warning_error = audio.load_sound(title_dir / "SE_ATTRACT_1.ogg")

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True
            tex.load_screen_textures('title')
            self.load_sounds()
            self.state = State.OP_VIDEO
            self.op_video = None
            self.attract_video = None
            self.warning_board = None
            self.fade_out = tex.get_animation(13)

    def on_screen_end(self) -> str:
        if self.op_video is not None:
            self.op_video.stop()
        if self.attract_video is not None:
            self.attract_video.stop()
        audio.unload_all_sounds()
        tex.unload_textures()
        self.screen_init = False
        return "ENTRY"

    def scene_manager(self):
        if self.state == State.OP_VIDEO:
            if self.op_video is None:
                self.op_video = VideoPlayer(random.choice(self.op_video_list))
                self.op_video.start(get_current_ms())
            self.op_video.update()
            if self.op_video.is_finished():
                self.op_video.stop()
                self.op_video = None
                self.state = State.WARNING
        elif self.state == State.WARNING:
            if self.warning_board is None:
                self.warning_board = WarningScreen(get_current_ms())
            self.warning_board.update(get_current_ms(), self)
            if self.warning_board.is_finished:
                self.state = State.ATTRACT_VIDEO
                self.warning_board = None
        elif self.state == State.ATTRACT_VIDEO:
            if self.attract_video is None:
                self.attract_video = VideoPlayer(random.choice(self.attract_video_list))
                self.attract_video.start(get_current_ms())
            self.attract_video.update()
            if self.attract_video.is_finished():
                self.attract_video.stop()
                self.attract_video = None
                self.state = State.OP_VIDEO


    def update(self):
        self.on_screen_start()

        self.fade_out.update(get_current_ms())
        if self.fade_out.is_finished:
            return self.on_screen_end()

        self.scene_manager()
        if is_l_don_pressed() or is_r_don_pressed():
            self.fade_out.start()
            audio.play_sound(self.sound_don)

    def draw(self):
        if self.state == State.OP_VIDEO and self.op_video is not None:
            self.op_video.draw()
        elif self.state == State.WARNING and self.warning_board is not None:
            tex.draw_texture('warning', 'background')
            self.warning_board.draw()
        elif self.state == State.ATTRACT_VIDEO and self.attract_video is not None:
            self.attract_video.draw()

        tex.draw_texture('movie', 'background', color=ray.fade(ray.WHITE, self.fade_out.attribute))

    def draw_3d(self):
        pass

class WarningScreen:
    class X:
        def __init__(self):
            self.resize = tex.get_animation(0)
            self.resize.start()
            self.fadein = tex.get_animation(1)
            self.fadein.start()
            self.fadein_2 = tex.get_animation(2)
            self.fadein_2.start()
            self.sound_played = False

        def update(self, current_ms: float, sound):
            self.resize.update(current_ms)
            self.fadein.update(current_ms)
            self.fadein_2.update(current_ms)

            if self.resize.attribute > 1 and not self.sound_played:
                audio.play_sound(sound)
                self.sound_played = True

        def draw_bg(self):
            tex.draw_texture('warning', 'x_lightred', color=ray.fade(ray.WHITE, self.fadein_2.attribute))

        def draw_fg(self):
            tex.draw_texture('warning', 'x_red', color=ray.fade(ray.WHITE, self.fadein.attribute), scale=self.resize.attribute, center=True)

    class BachiHit:
        def __init__(self):
            self.resize = tex.get_animation(3)
            self.fadein = tex.get_animation(4)

            self.sound_played = False

        def update(self, current_ms: float, sound):
            if not self.sound_played:
                audio.play_sound(sound)
                self.sound_played = True
                self.fadein.start()
                self.resize.start()
            self.resize.update(current_ms)
            self.fadein.update(current_ms)

        def draw(self):
            tex.draw_texture('warning', 'bachi_hit', color=ray.fade(ray.WHITE, self.fadein.attribute), scale=self.resize.attribute, center=True)
            if self.resize.attribute > 0 and self.sound_played:
                tex.draw_texture('warning', 'bachi')

    class Characters:
        def __init__(self):
            self.shadow_fade = tex.get_animation(5)
            self.chara_0_frame = tex.get_animation(7)
            self.chara_1_frame = tex.get_animation(6)
            self.chara_0_frame.start()
            self.chara_1_frame.start()
            self.saved_frame = 0
            self.is_finished = False

        def update(self, current_ms: float):
            self.shadow_fade.update(current_ms)
            self.chara_1_frame.update(current_ms)
            self.chara_0_frame.update(current_ms)
            self.current_ms = current_ms
            if self.chara_1_frame.attribute != self.saved_frame:
                self.saved_frame = self.chara_1_frame.attribute
                if not self.shadow_fade.is_started:
                    self.shadow_fade.start()
                else:
                    self.shadow_fade.restart()
            self.is_finished = self.chara_1_frame.is_finished
        def draw(self, fade: ray.Color, fade_2: ray.Color):
            tex.draw_texture('warning', 'chara_0_shadow', color=fade_2)
            tex.draw_texture('warning', 'chara_0', frame=self.chara_0_frame.attribute, color=fade)

            tex.draw_texture('warning', 'chara_1_shadow', color=fade_2)
            if -1 < self.chara_1_frame.attribute-1 < 7:
                tex.draw_texture('warning', 'chara_1', frame=self.chara_1_frame.attribute-1, color=ray.fade(ray.WHITE, self.shadow_fade.attribute))
            tex.draw_texture('warning', 'chara_1', frame=self.chara_1_frame.attribute, color=fade)

    class Board:
        def __init__(self):
            self.move_down = tex.get_animation(10)
            self.move_down.start()
            self.move_up = tex.get_animation(11)
            self.move_up.start()
            self.move_center = tex.get_animation(12)
            self.move_center.start()
            self.y_pos = 0

        def update(self, current_ms):
            self.move_down.update(current_ms)
            self.move_up.update(current_ms)
            self.move_center.update(current_ms)
            if self.move_up.is_finished:
                self.y_pos = self.move_center.attribute
            elif self.move_down.is_finished:
                self.y_pos = self.move_up.attribute
            else:
                self.y_pos = self.move_down.attribute
            tex.update_attr('warning', 'warning_box', 'y', self.y_pos)

        def draw(self):
            tex.draw_texture('warning', 'warning_box')


    def __init__(self, current_ms: float):
        self.start_ms = current_ms

        self.fade_in = tex.get_animation(8)
        self.fade_in.start()
        self.fade_out = tex.get_animation(9)
        self.fade_out.start()

        self.board = self.Board()
        self.warning_x = self.X()
        self.warning_bachi_hit = self.BachiHit()
        self.characters = self.Characters()

        self.is_finished = False

    def update(self, current_ms: float, title_screen: TitleScreen):
        self.board.update(current_ms)
        self.fade_in.update(current_ms)
        self.fade_out.update(current_ms)
        delay = 566.67
        elapsed_time = current_ms - self.start_ms
        self.warning_x.update(current_ms, title_screen.sound_warning_error)
        self.characters.update(current_ms)
        tex.update_attr('warning', 'chara_0', 'y', self.board.y_pos)
        tex.update_attr('warning', 'chara_0_shadow', 'y', self.board.y_pos)
        tex.update_attr('warning', 'chara_1_shadow', 'y', self.board.y_pos)
        tex.update_attr('warning', 'chara_1', 'y', self.board.y_pos)

        if self.characters.is_finished:
            self.warning_bachi_hit.update(current_ms, title_screen.sound_bachi_hit)
        else:
            self.fade_out.delay = elapsed_time + 500
            if delay <= elapsed_time and not audio.is_sound_playing(title_screen.sound_bachi_swipe):
                audio.play_sound(title_screen.sound_warning_message)
                audio.play_sound(title_screen.sound_bachi_swipe)

        self.is_finished = self.fade_out.is_finished

    def draw(self):
        fade = ray.fade(ray.WHITE, self.fade_in.attribute)
        fade_2 = ray.fade(ray.WHITE, min(self.fade_in.attribute, 0.75))

        self.board.draw()
        self.warning_x.draw_bg()
        self.characters.draw(fade, fade_2)
        self.warning_x.draw_fg()
        self.warning_bachi_hit.draw()

        tex.draw_texture('movie', 'background', color=ray.fade(ray.WHITE, self.fade_out.attribute))
