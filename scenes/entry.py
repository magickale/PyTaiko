import logging
from typing import Optional
import pyray as ray

from libs.audio import audio
from libs.chara_2d import Chara2D
from libs.global_data import PlayerNum
from libs.global_objects import AllNetIcon, CoinOverlay, Nameplate, Indicator, EntryOverlay, Timer
from libs.texture import tex
from libs.screen import Screen
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
)

logger = logging.getLogger(__name__)

class State:
    """State enum for the entry screen"""
    SELECT_SIDE = 0
    SELECT_MODE = 1

class EntryScreen(Screen):
    def on_screen_start(self):
        super().on_screen_start()
        self.side = 1
        self.is_2p = False
        self.box_manager = BoxManager()
        self.state = State.SELECT_SIDE

        # Initial nameplate for side selection
        plate_info = global_data.config['nameplate_1p']
        self.nameplate = Nameplate(plate_info['name'], plate_info['title'], PlayerNum.ALL, -1, False, False, 0)

        self.coin_overlay = CoinOverlay()
        self.allnet_indicator = AllNetIcon()
        self.entry_overlay = EntryOverlay()
        self.timer = Timer(60, get_current_ms(), self.box_manager.select_box)
        self.screen_init = True
        self.side_select_fade = tex.get_animation(0)
        self.bg_flicker = tex.get_animation(1)
        self.side_select_fade.start()
        self.chara = Chara2D(0)
        self.announce_played = False
        self.players: list[Optional[EntryPlayer]] = [None, None]
        audio.play_sound('bgm', 'music')

    def on_screen_end(self, next_screen: str):
        audio.stop_sound('bgm')
        self.nameplate.unload()
        for player in self.players:
            if player:
                player.unload()
        return super().on_screen_end(next_screen)

    def handle_input(self):
        if self.state == State.SELECT_SIDE:
            if is_l_don_pressed() or is_r_don_pressed():
                if self.side == 1:
                    return self.on_screen_end("TITLE")
                global_data.player_num = PlayerNum.P1 if self.side == 0 else PlayerNum.P2

                if self.players[0]:
                    self.players[1] = EntryPlayer(global_data.player_num, self.side, self.box_manager)
                    self.players[1].start_animations()
                    global_data.player_num = PlayerNum.P1
                    self.is_2p = True
                else:
                    self.players[0] = EntryPlayer(global_data.player_num, self.side, self.box_manager)
                    self.players[0].start_animations()
                    self.is_2p = False

                audio.play_sound('cloud', 'sound')
                audio.play_sound(f'entry_start_{global_data.player_num}p', 'voice')
                self.state = State.SELECT_MODE
                audio.play_sound('don', 'sound')
            if is_l_kat_pressed():
                audio.play_sound('kat', 'sound')
                if self.players[0] and self.players[0].player_num == PlayerNum.P1:
                    self.side = 1
                elif self.players[0] and self.players[0].player_num == PlayerNum.P2:
                    self.side = 0
                else:
                    self.side = max(0, self.side - 1)
            if is_r_kat_pressed():
                audio.play_sound('kat', 'sound')
                if self.players[0] and self.players[0].player_num == PlayerNum.P1:
                    self.side = 2
                elif self.players[0] and self.players[0].player_num == PlayerNum.P2:
                    self.side = 1
                else:
                    self.side = min(2, self.side + 1)
        elif self.state == State.SELECT_MODE:
            for player in self.players:
                if player:
                    player.handle_input()
            if self.players[0] and self.players[0].player_num == PlayerNum.P1 and is_l_don_pressed(PlayerNum.P2) or is_r_don_pressed(PlayerNum.P2):
                audio.play_sound('don', 'sound')
                self.state = State.SELECT_SIDE
                plate_info = global_data.config['nameplate_2p']
                self.nameplate = Nameplate(plate_info['name'], plate_info['title'], PlayerNum.ALL, -1, False, False, 1)
                self.chara = Chara2D(1)
                self.side_select_fade.restart()
                self.side = 1
            elif self.players[0] and self.players[0].player_num == PlayerNum.P2 and is_l_don_pressed(PlayerNum.P1) or is_r_don_pressed(PlayerNum.P1):
                audio.play_sound('don', 'sound')
                self.state = State.SELECT_SIDE
                self.side_select_fade.restart()
                self.side = 1

    def update(self):
        super().update()
        current_time = get_current_ms()
        self.side_select_fade.update(current_time)
        self.bg_flicker.update(current_time)
        self.box_manager.update(current_time, self.is_2p)
        self.timer.update(current_time)
        self.nameplate.update(current_time)
        self.chara.update(current_time, 100, False, False)
        for player in self.players:
            if player:
                player.update(current_time)
        if self.box_manager.is_finished():
            logger.info(f"Box selection finished, transitioning to {self.box_manager.selected_box()}")
            return self.on_screen_end(self.box_manager.selected_box())
        for player in self.players:
            if player and player.cloud_fade.is_finished and not audio.is_sound_playing(f'entry_start_{global_data.player_num}p') and not self.announce_played:
                audio.play_sound('select_mode', 'voice')
                self.announce_played = True
        return self.handle_input()

    def draw_background(self):
        tex.draw_texture('background', 'bg')
        tex.draw_texture('background', 'tower')
        tex.draw_texture('background', 'shops_center')
        tex.draw_texture('background', 'people')
        tex.draw_texture('background', 'shops_left')
        tex.draw_texture('background', 'shops_right')
        tex.draw_texture('background', 'lights', scale=2.0, fade=self.bg_flicker.attribute)


    def draw_side_select(self, fade):
        tex.draw_texture('side_select', 'box_top_left', fade=fade)
        tex.draw_texture('side_select', 'box_top_right', fade=fade)
        tex.draw_texture('side_select', 'box_bottom_left', fade=fade)
        tex.draw_texture('side_select', 'box_bottom_right', fade=fade)

        tex.draw_texture('side_select', 'box_top', fade=fade)
        tex.draw_texture('side_select', 'box_bottom', fade=fade)
        tex.draw_texture('side_select', 'box_left', fade=fade)
        tex.draw_texture('side_select', 'box_right', fade=fade)
        tex.draw_texture('side_select', 'box_center', fade=fade)

        tex.draw_texture('side_select', 'question', fade=fade)

        self.chara.draw(tex.skin_config["chara_entry"].x, tex.skin_config["chara_entry"].y)

        tex.draw_texture('side_select', '1P', fade=fade)
        tex.draw_texture('side_select', 'cancel', fade=fade)
        tex.draw_texture('side_select', '2P', fade=fade)
        if self.side == 0:
            tex.draw_texture('side_select', '1P_highlight', fade=fade)
            tex.draw_texture('side_select', '1P2P_outline', index=0, fade=fade, mirror='horizontal')
        elif self.side == 1:
            tex.draw_texture('side_select', 'cancel_highlight', fade=fade)
            tex.draw_texture('side_select', 'cancel_outline', fade=fade)
        else:
            tex.draw_texture('side_select', '2P_highlight', fade=fade)
            tex.draw_texture('side_select', '1P2P_outline', index=1, fade=fade)
        tex.draw_texture('side_select', 'cancel_text', fade=fade)
        self.nameplate.draw(tex.skin_config["nameplate_entry"].x, tex.skin_config["nameplate_entry"].y)

    def draw_player_drum(self):
        for player in self.players:
            if player:
                player.draw_drum()

    def draw_mode_select(self):
        for player in self.players:
            if player and not player.is_cloud_animation_finished():
                return
        self.box_manager.draw()

    def draw(self):
        self.draw_background()
        self.draw_player_drum()
        if self.state == State.SELECT_SIDE:
            self.draw_side_select(self.side_select_fade.attribute)
        elif self.state == State.SELECT_MODE:
            self.draw_mode_select()
        tex.draw_texture('side_select', 'footer')
        if self.players[0] and self.players[1]:
            pass
        elif not self.players[0]:
            tex.draw_texture('side_select', 'footer_left')
            tex.draw_texture('side_select', 'footer_right')
        elif self.players[0] and self.players[0].player_num == PlayerNum.P1:
            tex.draw_texture('side_select', 'footer_right')
        elif self.players[0] and self.players[0].player_num == PlayerNum.P2:
            tex.draw_texture('side_select', 'footer_left')


        for player in self.players:
            if player:
                player.draw_nameplate_and_indicator(fade=player.nameplate_fadein.attribute)

        tex.draw_texture('global', 'player_entry')

        if self.box_manager.is_finished():
            ray.draw_rectangle(0, 0, tex.screen_width, tex.screen_height, ray.BLACK)

        self.timer.draw()
        self.entry_overlay.draw(y=tex.skin_config['entry_overlay_entry'].y)
        self.coin_overlay.draw()
        self.allnet_indicator.draw()

class EntryPlayer:
    """Player-specific state and rendering for the entry screen"""
    def __init__(self, player_num: PlayerNum, side: int, box_manager: 'BoxManager'):
        """
        Initialize a player for the entry screen
        Args:
            player_num: 1 or 2 (player number)
            side: 0 for left (1P), 2 for right (2P)
            box_manager: Reference to the box manager for input handling
        """
        self.player_num = player_num
        self.side = side
        self.box_manager = box_manager

        # Load player-specific resources
        plate_info = global_data.config[f'nameplate_{self.player_num}p']
        self.nameplate = Nameplate(
            plate_info['name'],
            plate_info['title'],
            player_num,
            plate_info['dan'],
            plate_info['gold'],
            plate_info['rainbow'],
            plate_info['title_bg']
        )
        self.indicator = Indicator(Indicator.State.SELECT)

        # Character (0 for red/1P, 1 for blue/2P)
        chara_id = 0 if side == 0 else 1
        self.chara = Chara2D(chara_id)

        # Animations
        self.drum_move_1 = tex.get_animation(2)
        self.drum_move_2 = tex.get_animation(3)
        self.drum_move_3 = tex.get_animation(4)
        self.cloud_resize = tex.get_animation(5)
        self.cloud_resize_loop = tex.get_animation(6)
        self.cloud_texture_change = tex.get_animation(7)
        self.cloud_fade = tex.get_animation(8)
        self.nameplate_fadein = tex.get_animation(12)

    def start_animations(self):
        """Start all player entry animations"""
        self.drum_move_1.start()
        self.drum_move_2.start()
        self.drum_move_3.start()
        self.cloud_resize.start()
        self.cloud_resize_loop.start()
        self.cloud_texture_change.start()
        self.cloud_fade.start()
        self.nameplate_fadein.start()

    def update(self, current_time: float):
        """Update player animations and state"""
        self.drum_move_1.update(current_time)
        self.drum_move_2.update(current_time)
        self.drum_move_3.update(current_time)
        self.cloud_resize.update(current_time)
        self.cloud_texture_change.update(current_time)
        self.cloud_fade.update(current_time)
        self.cloud_resize_loop.update(current_time)
        self.nameplate_fadein.update(current_time)
        self.nameplate.update(current_time)
        self.indicator.update(current_time)
        self.chara.update(current_time)

    def draw_drum(self):
        """Draw the player's drum with animations"""
        move_x = self.drum_move_3.attribute
        move_y = self.drum_move_1.attribute + self.drum_move_2.attribute

        if self.side == 0:  # Left side (1P/red)
            offset = tex.skin_config["entry_drum_offset"].x
            tex.draw_texture('side_select', 'red_drum', x=move_x, y=move_y)
            chara_x = move_x + offset + tex.skin_config["entry_chara_offset_l"].x
            chara_mirror = False
        else:  # Right side (2P/blue)
            move_x *= -1
            offset = tex.skin_config["entry_drum_offset"].y # bad practice to use y value as x value
            tex.draw_texture('side_select', 'blue_drum', x=move_x, y=move_y)
            chara_x = move_x + offset + tex.skin_config["entry_chara_offset_r"].x
            chara_mirror = True

        # Draw character
        chara_y = tex.skin_config["entry_chara_offset_r"].y + move_y
        self.chara.draw(chara_x, chara_y, mirror=chara_mirror)

        # Draw cloud
        scale = self.cloud_resize.attribute
        if self.cloud_resize.is_finished:
            scale = max(1, self.cloud_resize_loop.attribute)
        tex.draw_texture(
            'side_select', 'cloud',
            x=move_x + offset,
            y=move_y,
            frame=self.cloud_texture_change.attribute,
            fade=self.cloud_fade.attribute,
            scale=scale,
            center=True
        )

    def draw_nameplate_and_indicator(self, fade: float = 1.0):
        """Draw nameplate and indicator at player-specific position"""
        if self.side == 0:  # Left side
            self.nameplate.draw(tex.skin_config['nameplate_entry_left'].x, tex.skin_config['nameplate_entry_left'].y, fade=fade)
            self.indicator.draw(tex.skin_config['indicator_entry_left'].x, tex.skin_config['indicator_entry_left'].y, fade=fade)
        else:  # Right side
            self.nameplate.draw(tex.skin_config['nameplate_entry_right'].x, tex.skin_config['nameplate_entry_right'].y, fade=fade)
            self.indicator.draw(tex.skin_config['indicator_entry_right'].x, tex.skin_config['indicator_entry_right'].y, fade=fade)

    def is_cloud_animation_finished(self) -> bool:
        """Check if cloud texture change animation is finished"""
        return self.cloud_texture_change.is_finished

    def unload(self):
        """Unload player resources"""
        self.nameplate.unload()

    def handle_input(self):
        """Handle player input for mode selection"""
        if self.box_manager.is_box_selected():
            return

        if is_l_don_pressed(self.player_num) or is_r_don_pressed(self.player_num):
            audio.play_sound('don', 'sound')
            self.box_manager.select_box()
        if is_l_kat_pressed(self.player_num):
            audio.play_sound('kat', 'sound')
            self.box_manager.move_left()
        if is_r_kat_pressed(self.player_num):
            audio.play_sound('kat', 'sound')
            self.box_manager.move_right()

class Box:
    """Box class for the entry screen"""
    def __init__(self, text: OutlinedText, location: str):
        self.text = text
        self.location = location
        self.box_tex_obj = tex.textures['mode_select']['box']
        if isinstance(self.box_tex_obj.texture, list):
            raise Exception("Box texture cannot be iterable")
        self.texture = self.box_tex_obj.texture
        self.x = self.box_tex_obj.x[0]
        self.y = self.box_tex_obj.y[0]
        self.move = tex.get_animation(10)
        self.open = tex.get_animation(11)
        self.is_selected = False
        self.moving_left = False
        self.moving_right = False
        self.outline_color = ray.Color(109, 68, 24, 255)

    def set_positions(self, x: int):
        """Set the positions of the box"""
        self.x = x
        self.static_x = self.x
        self.left_x = self.x
        self.static_left = self.left_x
        self.right_x = self.left_x + tex.textures['mode_select']['box'].width - tex.textures['mode_select']['box_highlight_right'].width
        self.static_right = self.right_x

    def update(self, current_time_ms: float, is_selected: bool):
        self.move.update(current_time_ms)
        if self.moving_left:
            self.x = self.static_x - int(self.move.attribute)
        elif self.moving_right:
            self.x = self.static_x + int(self.move.attribute)
        if self.move.is_finished:
            self.moving_left = False
            self.moving_right = False
            self.static_x = self.x

        if is_selected and not self.is_selected:
            self.open.start()
        self.is_selected = is_selected
        if self.is_selected:
            self.left_x = self.static_left - int(self.open.attribute)
            self.right_x = self.static_right + int(self.open.attribute)
        self.open.update(current_time_ms)

    def move_left(self):
        """Move the box left"""
        if not self.move.is_started:
            self.move.start()
        self.moving_left = True

    def move_right(self):
        """Move the box right"""
        if not self.move.is_started:
            self.move.start()
        self.moving_right = True

    def _draw_highlighted(self, color):
        texture_left = tex.textures['mode_select']['box_highlight_left'].texture
        if isinstance(texture_left, list):
            raise Exception("highlight textures cannot be iterable")
        tex.draw_texture('mode_select', 'box_highlight_center', x=self.left_x + texture_left.width, y=self.y, x2=self.right_x - self.left_x + tex.skin_config["entry_box_highlight_offset"].x, color=color)
        tex.draw_texture('mode_select', 'box_highlight_left', x=self.left_x, y=self.y, color=color)
        tex.draw_texture('mode_select', 'box_highlight_right', x=self.right_x, y=self.y, color=color)

    def _draw_text(self, color):
        text_x = self.x + (self.texture.width//2) - (self.text.texture.width//2)
        if self.is_selected:
            text_x += self.open.attribute
        text_y = self.y + tex.skin_config["entry_box_text_offset"].y
        if self.is_selected:
            self.text.draw(outline_color=ray.BLACK, x=text_x, y=text_y, color=color)
        else:
            self.text.draw(outline_color=self.outline_color, x=text_x, y=text_y, color=color)

    def draw(self, fade: float):
        color = ray.fade(ray.WHITE, fade)
        ray.draw_texture(self.texture, int(self.x), int(self.y), color)
        if self.is_selected and self.move.is_finished:
            self._draw_highlighted(color)
        self._draw_text(color)

class BoxManager:
    """BoxManager class for the entry screen"""
    def __init__(self):
        self.box_titles: list[OutlinedText] = [
        OutlinedText('演奏ゲーム', tex.skin_config["entry_box_text"].font_size, ray.WHITE, outline_thickness=5, vertical=True),
        OutlinedText('特訓モード', tex.skin_config["entry_box_text"].font_size, ray.WHITE, outline_thickness=5, vertical=True),
        OutlinedText('ゲーム設定', tex.skin_config["entry_box_text"].font_size, ray.WHITE, outline_thickness=5, vertical=True)]
        self.box_locations = ["SONG_SELECT", "PRACTICE_SELECT", "SETTINGS"]
        self.num_boxes = len(self.box_titles)
        self.boxes = [Box(self.box_titles[i], self.box_locations[i]) for i in range(len(self.box_titles))]
        self.selected_box_index = 0
        self.fade_out = tex.get_animation(9)
        self.is_2p = False

        spacing = tex.skin_config["entry_box_spacing"].x
        box_width = self.boxes[0].texture.width
        total_width = self.num_boxes * box_width + (self.num_boxes - 1) * spacing
        start_x = tex.screen_width//2 - total_width//2
        for i, box in enumerate(self.boxes):
            box.set_positions(start_x + i * (box_width + spacing))
            if i > 0:
                box.move_right()

    def select_box(self):
        """Select the currently selected box"""
        self.fade_out.start()

    def is_box_selected(self):
        """Check if the box is selected"""
        return self.fade_out.is_started

    def is_finished(self):
        """Check if the animation is finished"""
        return self.fade_out.is_finished

    def selected_box(self):
        """Get the location of the currently selected box"""
        return self.boxes[self.selected_box_index].location

    def move_left(self):
        """Move the cursor to the left"""
        prev_selection = self.selected_box_index
        if self.boxes[prev_selection].move.is_started and not self.boxes[prev_selection].move.is_finished:
            return
        self.selected_box_index = max(0, self.selected_box_index - 1)
        if prev_selection == self.selected_box_index:
            return
        if self.selected_box_index != self.selected_box_index - 1:
            self.boxes[self.selected_box_index+1].move_right()
        self.boxes[self.selected_box_index].move_right()

    def move_right(self):
        """Move the cursor to the right"""
        prev_selection = self.selected_box_index
        if self.boxes[prev_selection].move.is_started and not self.boxes[prev_selection].move.is_finished:
            return
        self.selected_box_index = min(self.num_boxes - 1, self.selected_box_index + 1)
        if prev_selection == self.selected_box_index:
            return
        if self.selected_box_index != 0:
            self.boxes[self.selected_box_index-1].move_left()
        self.boxes[self.selected_box_index].move_left()

    def update(self, current_time_ms: float, is_2p: bool):
        self.is_2p = is_2p
        if self.is_2p:
            self.box_locations = ["SONG_SELECT_2P", "PRACTICE_SELECT", "SETTINGS"]
            for i, box in enumerate(self.boxes):
                box.location = self.box_locations[i]
        self.fade_out.update(current_time_ms)
        for i, box in enumerate(self.boxes):
            is_selected = i == self.selected_box_index
            box.update(current_time_ms, is_selected)

    def draw(self):
        for box in self.boxes:
            box.draw(self.fade_out.attribute)
