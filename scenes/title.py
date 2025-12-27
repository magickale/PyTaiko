import logging
import random
from pathlib import Path

import pyray as ray

from libs.audio import audio
from libs.global_objects import AllNetIcon, CoinOverlay, EntryOverlay
from libs.screen import Screen
from libs.texture import tex
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    global_tex,
    is_l_don_pressed,
    is_r_don_pressed,
)
from libs.video import VideoPlayer

logger = logging.getLogger(__name__)

class State:
    OP_VIDEO = 0
    WARNING = 1
    ATTRACT_VIDEO = 2

class TitleScreen(Screen):
    def __init__(self, name: str):
        super().__init__(name)
        self.op_video_list = []
        self.attract_video_list = []
        base = Path(f"Skins/{global_data.config["paths"]["skin"]}/Videos")
        self.op_video_list += list((base/"op_videos").glob("**/*.mp4"))
        self.attract_video_list += list((base/"attract_videos").glob("**/*.mp4"))

    def on_screen_start(self):
        super().on_screen_start()
        self.state = State.OP_VIDEO
        self.op_video = None
        self.attract_video = None
        self.warning_board = None
        self.coin_overlay = CoinOverlay()
        self.allnet_indicator = AllNetIcon()
        self.entry_overlay = EntryOverlay()
        self.hit_taiko_text = OutlinedText(global_tex.skin_config["hit_taiko_to_start"].text[global_data.config["general"]["language"]], tex.skin_config["hit_taiko_to_start"].font_size, ray.WHITE, spacing=5)
        self.fade_out = tex.get_animation(13)
        self.text_overlay_fade = tex.get_animation(14)

    def on_screen_end(self, next_screen) -> str:
        if self.op_video is not None:
            self.op_video.stop()
            logger.info("OP video stopped")
        if self.attract_video is not None:
            self.attract_video.stop()
            logger.info("Attract video stopped")
        return super().on_screen_end(next_screen)

    def scene_manager(self, current_time):
        """Manage the scene transitions"""
        if self.state == State.OP_VIDEO:
            if self.op_video is None:
                self.op_video = VideoPlayer(random.choice(self.op_video_list))
                self.op_video.start(current_time)
                logger.info("Started OP video")
            self.op_video.update()
            if self.op_video.is_finished():
                self.op_video.stop()
                self.op_video = None
                self.state = State.WARNING
                logger.info("OP video finished, transitioning to WARNING state")
        elif self.state == State.WARNING:
            if self.warning_board is None:
                self.warning_board = WarningScreen(current_time)
                logger.info("Warning screen started")
            self.warning_board.update(current_time)
            if self.warning_board.is_finished:
                self.state = State.ATTRACT_VIDEO
                self.warning_board = None
                logger.info("Warning finished, transitioning to ATTRACT_VIDEO state")
        elif self.state == State.ATTRACT_VIDEO:
            if self.attract_video is None:
                self.attract_video = VideoPlayer(random.choice(self.attract_video_list))
                self.attract_video.start(current_time)
                logger.info("Started attract video")
            self.attract_video.update()
            if self.attract_video.is_finished():
                self.attract_video.stop()
                self.attract_video = None
                self.state = State.OP_VIDEO
                logger.info("Attract video finished, transitioning to OP_VIDEO state")


    def update(self):
        super().update()
        current_time = get_current_ms()

        self.text_overlay_fade.update(current_time)
        self.fade_out.update(current_time)
        if self.fade_out.is_finished:
            self.fade_out.update(current_time)
            return self.on_screen_end("ENTRY")

        self.scene_manager(current_time)
        if is_l_don_pressed() or is_r_don_pressed():
            self.fade_out.start()
            audio.play_sound('don', 'sound')

    def draw(self):
        if self.state == State.OP_VIDEO and self.op_video is not None:
            self.op_video.draw()
        elif self.state == State.WARNING and self.warning_board is not None:
            tex.draw_texture('warning', 'background')
            self.warning_board.draw()
        elif self.state == State.ATTRACT_VIDEO and self.attract_video is not None:
            self.attract_video.draw()

        tex.draw_texture('movie', 'background', fade=self.fade_out.attribute)
        self.coin_overlay.draw()
        self.allnet_indicator.draw()
        self.entry_overlay.draw(tex.skin_config["entry_overlay_title"].x, y=tex.skin_config["entry_overlay_title"].y)

        self.hit_taiko_text.draw(ray.BLACK, x=tex.screen_width*0.25 - self.hit_taiko_text.texture.width//2, y=tex.skin_config["hit_taiko_to_start"].y, fade=self.text_overlay_fade.attribute)
        self.hit_taiko_text.draw(ray.BLACK, x=tex.screen_width*0.75 - self.hit_taiko_text.texture.width//2, y=tex.skin_config["hit_taiko_to_start"].y, fade=self.text_overlay_fade.attribute)

class WarningScreen:
    """Warning screen for the game"""
    class X:
        """Giant X behind the characters for the warning screen"""
        def __init__(self):
            self.resize = tex.get_animation(0)
            self.resize.start()
            self.fadein = tex.get_animation(1)
            self.fadein.start()
            self.fadein_2 = tex.get_animation(2)
            self.fadein_2.start()
            self.sound_played = False

        def update(self, current_ms: float):
            self.resize.update(current_ms)
            self.fadein.update(current_ms)
            self.fadein_2.update(current_ms)

            if self.resize.attribute > 1 and not self.sound_played:
                audio.play_sound('error', 'attract_mode')
                self.sound_played = True

        def draw_bg(self):
            tex.draw_texture('warning', 'x_lightred', fade=self.fadein_2.attribute)

        def draw_fg(self):
            tex.draw_texture('warning', 'x_red', fade=self.fadein.attribute, scale=self.resize.attribute, center=True)

    class BachiHit:
        """Bachi hitting the player animation for the warning screen"""
        def __init__(self):
            self.resize = tex.get_animation(3)
            self.fadein = tex.get_animation(4)

            self.sound_played = False

        def update(self, current_ms: float):
            if not self.sound_played:
                audio.play_sound('bachi_hit', 'attract_mode')
                self.sound_played = True
                self.fadein.start()
                self.resize.start()
            self.resize.update(current_ms)
            self.fadein.update(current_ms)

        def draw(self):
            tex.draw_texture('warning', 'bachi_hit', fade=self.fadein.attribute, scale=self.resize.attribute, center=True)
            if self.resize.attribute > 0 and self.sound_played:
                tex.draw_texture('warning', 'bachi')

    class Characters:
        """Characters for the warning screen"""
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
        def draw(self, fade: float, fade_2: float, y_pos: float):
            tex.draw_texture('warning', 'chara_0_shadow', fade=fade_2, y=y_pos)
            tex.draw_texture('warning', 'chara_0', frame=self.chara_0_frame.attribute, fade=fade, y=y_pos)

            tex.draw_texture('warning', 'chara_1_shadow', fade=fade_2, y=y_pos)
            if -1 < self.chara_1_frame.attribute-1 < 7:
                tex.draw_texture('warning', 'chara_1', frame=self.chara_1_frame.attribute-1, fade=self.shadow_fade.attribute, y=y_pos)
            tex.draw_texture('warning', 'chara_1', frame=self.chara_1_frame.attribute, fade=fade, y=y_pos)

    class Board:
        """Background Board for the warning screen"""
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

        def draw(self):
            tex.draw_texture('warning', 'warning_box', y=self.y_pos)


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

    def update(self, current_ms: float):
        self.board.update(current_ms)
        self.fade_in.update(current_ms)
        self.fade_out.update(current_ms)
        delay = 566.67
        fade_out_delay = 500
        elapsed_time = current_ms - self.start_ms
        self.warning_x.update(current_ms)
        self.characters.update(current_ms)

        if self.characters.is_finished:
            self.warning_bachi_hit.update(current_ms)
        else:
            self.fade_out.delay = elapsed_time + fade_out_delay
            if delay <= elapsed_time and not audio.is_sound_playing('bachi_swipe'):
                audio.play_sound('warning_voiceover', 'attract_mode')
                audio.play_sound('bachi_swipe', 'attract_mode')

        self.is_finished = self.fade_out.is_finished

    def draw(self):
        self.board.draw()
        self.warning_x.draw_bg()
        self.characters.draw(self.fade_in.attribute, min(self.fade_in.attribute, 0.75), self.board.y_pos)
        self.warning_x.draw_fg()
        self.warning_bachi_hit.draw()

        tex.draw_texture('movie', 'background', fade=self.fade_out.attribute)
