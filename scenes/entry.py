from pathlib import Path

import pyray as ray

from libs.audio import audio
from libs.texture import tex
from libs.utils import (
    OutlinedText,
    get_current_ms,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
)


class State:
    SELECT_SIDE = 0
    SELECT_MODE = 1

class EntryScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.screen_init = False

    def load_textures(self):
        tex.load_screen_textures('entry')

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(sounds_dir / "inst_00_don.wav")
        self.sound_kat = audio.load_sound(sounds_dir / "inst_00_katsu.wav")
        self.bgm = audio.load_sound(sounds_dir / "entry" / "JINGLE_ENTRY [1].ogg")

    def on_screen_start(self):
        if not self.screen_init:
            self.load_textures()
            self.load_sounds()
            self.side = 1
            self.box_manager = BoxManager()
            self.state = State.SELECT_SIDE
            self.screen_init = True
            self.side_select_fade = tex.get_animation(0)
            self.bg_flicker = tex.get_animation(1)
            self.drum_move_1 = tex.get_animation(2)
            self.drum_move_2 = tex.get_animation(3)
            self.drum_move_3 = tex.get_animation(4)
            self.cloud_resize = tex.get_animation(5)
            self.cloud_resize_loop = tex.get_animation(6)
            self.cloud_texture_change = tex.get_animation(7)
            self.cloud_fade = tex.get_animation(8)
            self.cloud_resize_loop.start()
            self.side_select_fade.start()
            self.bg_flicker.start()
            audio.play_sound(self.bgm)

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        audio.stop_sound(self.bgm)
        tex.unload_textures()
        audio.unload_all_sounds()
        return next_screen

    def handle_input(self):
        if self.box_manager.is_box_selected():
            return
        if self.state == State.SELECT_SIDE:
            if is_l_don_pressed() or is_r_don_pressed():
                if self.side == 1:
                    return self.on_screen_end("TITLE")
                self.drum_move_1.start()
                self.drum_move_2.start()
                self.drum_move_3.start()
                self.cloud_resize.start()
                self.cloud_resize_loop.start()
                self.cloud_texture_change.start()
                self.cloud_fade.start()
                self.state = State.SELECT_MODE
                audio.play_sound(self.sound_don)
            if is_l_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.side = max(0, self.side - 1)
            if is_r_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.side = min(2, self.side + 1)
        elif self.state == State.SELECT_MODE:
            if is_l_don_pressed() or is_r_don_pressed():
                audio.play_sound(self.sound_don)
                self.box_manager.select_box()
            if is_l_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.box_manager.move_left()
            if is_r_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.box_manager.move_right()

    def update(self):
        self.on_screen_start()
        self.side_select_fade.update(get_current_ms())
        self.bg_flicker.update(get_current_ms())
        if self.bg_flicker.is_finished:
            self.bg_flicker.restart()
        self.drum_move_1.update(get_current_ms())
        self.drum_move_2.update(get_current_ms())
        self.drum_move_3.update(get_current_ms())
        self.cloud_resize.update(get_current_ms())
        self.cloud_texture_change.update(get_current_ms())
        self.cloud_fade.update(get_current_ms())
        self.cloud_resize_loop.update(get_current_ms())
        if self.cloud_resize_loop.is_finished:
            self.cloud_resize_loop.restart()
        self.box_manager.update(get_current_ms())
        if self.box_manager.is_finished():
            return self.on_screen_end(self.box_manager.selected_box())
        return self.handle_input()

    def draw_background(self):
        tex.draw_texture('background', 'bg')
        tex.draw_texture('background', 'tower')
        tex.draw_texture('background', 'shops_center')
        tex.draw_texture('background', 'people')
        tex.draw_texture('background', 'shops_left')
        tex.draw_texture('background', 'shops_right')
        tex.draw_texture('background', 'lights', scale=2.0, color=ray.fade(ray.WHITE, self.bg_flicker.attribute))

    def draw_footer(self):
        tex.draw_texture('side_select', 'footer')
        if self.state == State.SELECT_SIDE or self.side != 0:
            tex.draw_texture('side_select', 'footer_left')
        if self.state == State.SELECT_SIDE or self.side != 2:
            tex.draw_texture('side_select', 'footer_right')

    def draw_side_select(self, fade):
        color = ray.fade(ray.WHITE, fade)
        tex.draw_texture('side_select', 'box_top_left', color=color)
        tex.draw_texture('side_select', 'box_top_right', color=color)
        tex.draw_texture('side_select', 'box_bottom_left', color=color)
        tex.draw_texture('side_select', 'box_bottom_right', color=color)

        tex.draw_texture('side_select', 'box_top', color=color)
        tex.draw_texture('side_select', 'box_bottom', color=color)
        tex.draw_texture('side_select', 'box_left', color=color)
        tex.draw_texture('side_select', 'box_right', color=color)
        tex.draw_texture('side_select', 'box_center', color=color)

        tex.draw_texture('side_select', 'question', color=color)

        tex.draw_texture('side_select', '1P', color=color)
        tex.draw_texture('side_select', 'cancel', color=color)
        tex.draw_texture('side_select', '2P', color=color)
        if self.side == 0:
            tex.draw_texture('side_select', '1P_highlight', color=color)
            tex.textures['side_select']['1P2P_outline'].x = 261
            tex.draw_texture('side_select', '1P2P_outline', color=color, mirror='horizontal')
        elif self.side == 1:
            tex.draw_texture('side_select', 'cancel_highlight', color=color)
            tex.draw_texture('side_select', 'cancel_outline', color=color)
        else:
            tex.draw_texture('side_select', '2P_highlight', color=color)
            tex.textures['side_select']['1P2P_outline'].x = 762
            tex.draw_texture('side_select', '1P2P_outline', color=color)
        tex.draw_texture('side_select', 'cancel_text', color=color)

    def draw_player_drum(self):
        move_x = self.drum_move_3.attribute
        move_y = self.drum_move_1.attribute + self.drum_move_2.attribute
        tex.update_attr('side_select', 'red_drum', 'x', move_x)
        tex.update_attr('side_select', 'red_drum', 'y', move_y)
        tex.update_attr('side_select', 'blue_drum', 'y', move_y)
        if self.side == 0:
            tex.draw_texture('side_select', 'red_drum')
        else:
            move_x *= -1
            tex.textures['side_select']['cloud'].init_vals['x'] = tex.textures['side_select']['blue_drum'].init_vals['x']
            tex.update_attr('side_select', 'blue_drum', 'x', move_x)
            tex.draw_texture('side_select', 'blue_drum')

        scale = self.cloud_resize.attribute
        if self.cloud_resize.is_finished:
            scale = max(1, self.cloud_resize_loop.attribute)
        color = ray.fade(ray.WHITE, self.cloud_fade.attribute)
        tex.update_attr('side_select', 'cloud', 'x', move_x)
        tex.update_attr('side_select', 'cloud', 'y', move_y)
        tex.draw_texture('side_select', 'cloud', frame=self.cloud_texture_change.attribute, color=color, scale=scale, center=True)

    def draw_mode_select(self):
        self.draw_player_drum()
        if not self.cloud_texture_change.is_finished:
            return
        self.box_manager.draw()

    def draw(self):
        self.draw_background()
        if self.state == State.SELECT_SIDE:
            self.draw_side_select(self.side_select_fade.attribute)
        elif self.state == State.SELECT_MODE:
            self.draw_mode_select()
        self.draw_footer()

        tex.draw_texture('global', 'player_entry')

        if self.box_manager.is_finished():
            ray.draw_rectangle(0, 0, self.width, self.height, ray.BLACK)

    def draw_3d(self):
        pass

class Box:
    def __init__(self, text: tuple[OutlinedText, OutlinedText], location: str):
        self.text, self.text_highlight = text
        self.location = location
        self.box_tex_obj = tex.textures['mode_select']['box']
        if isinstance(self.box_tex_obj.texture, list):
            raise Exception("Box texture cannot be iterable")
        self.texture = self.box_tex_obj.texture
        self.x = self.box_tex_obj.x
        self.y = self.box_tex_obj.y
        self.move = tex.get_animation(10)
        self.open = tex.get_animation(11)
        self.is_selected = False
        self.moving_left = False
        self.moving_right = False

    def set_positions(self, x: int):
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
        if not self.move.is_started:
            self.move.start()
        self.moving_left = True

    def move_right(self):
        if not self.move.is_started:
            self.move.start()
        self.moving_right = True

    def _draw_highlighted(self, color):
        texture_left = tex.textures['mode_select']['box_highlight_left'].texture
        texture_center = tex.textures['mode_select']['box_highlight_center'].texture
        texture_right = tex.textures['mode_select']['box_highlight_right'].texture
        if isinstance(texture_center, list) or isinstance(texture_left, list):
            raise Exception("highlight textures cannot be iterable")
        center_src = ray.Rectangle(0, 0, texture_center.width, texture_center.height)
        center_dest = ray.Rectangle(self.left_x + texture_left.width, self.y, self.right_x - self.left_x, texture_center.height)
        ray.draw_texture_pro(texture_center, center_src, center_dest, ray.Vector2(0, 0), 0, color)
        ray.draw_texture(texture_center, self.left_x, self.y, color)
        ray.draw_texture(texture_left, self.left_x, self.y, color)
        ray.draw_texture(texture_right, self.right_x, self.y, color)

    def _draw_text(self, color):
        text_x = self.x + (self.texture.width//2) - (self.text.texture.width//2)
        text_y = self.y + 20
        text_dest = ray.Rectangle(text_x, text_y, self.text.texture.width, self.text.texture.height)
        if self.is_selected:
            self.text_highlight.draw(self.text.default_src, text_dest, ray.Vector2(0, 0), 0, color)
        else:
            self.text.draw(self.text.default_src, text_dest, ray.Vector2(0, 0), 0, color)

    def draw(self, fade: float):
        color = ray.fade(ray.WHITE, fade)
        ray.draw_texture(self.texture, self.x, self.y, color)
        if self.is_selected and self.move.is_finished:
            self._draw_highlighted(color)
        self._draw_text(color)

class BoxManager:
    def __init__(self):
        self.box_titles: list[tuple[OutlinedText, OutlinedText]] = [
        (OutlinedText('演奏ゲーム', 50, ray.WHITE, ray.Color(109, 68, 24, 255), outline_thickness=5, vertical=True),
         OutlinedText('演奏ゲーム', 50, ray.WHITE, ray.BLACK, outline_thickness=5, vertical=True)),
        (OutlinedText('ゲーム設定', 50, ray.WHITE, ray.Color(109, 68, 24, 255), outline_thickness=5, vertical=True),
         OutlinedText('ゲーム設定', 50, ray.WHITE, ray.BLACK, outline_thickness=5, vertical=True))]
        self.box_locations = ["SONG_SELECT", "SETTINGS"]
        self.num_boxes = len(self.box_titles)
        self.boxes = [Box(self.box_titles[i], self.box_locations[i]) for i in range(len(self.box_titles))]
        self.selected_box_index = 0
        self.fade_out = tex.get_animation(9)

        spacing = 80
        box_width = self.boxes[0].texture.width
        total_width = self.num_boxes * box_width + (self.num_boxes - 1) * spacing
        start_x = 640 - total_width//2
        for i, box in enumerate(self.boxes):
            box.set_positions(start_x + i * (box_width + spacing))
            if i > 0:
                box.move_right()

    def select_box(self):
        self.fade_out.start()

    def is_box_selected(self):
        return self.fade_out.is_started

    def is_finished(self):
        return self.fade_out.is_finished

    def selected_box(self):
        return self.boxes[self.selected_box_index].location

    def move_left(self):
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
        prev_selection = self.selected_box_index
        if self.boxes[prev_selection].move.is_started and not self.boxes[prev_selection].move.is_finished:
            return
        self.selected_box_index = min(self.num_boxes - 1, self.selected_box_index + 1)
        if prev_selection == self.selected_box_index:
            return
        if self.selected_box_index != 0:
            self.boxes[self.selected_box_index-1].move_left()
        self.boxes[self.selected_box_index].move_left()

    def update(self, current_time_ms: float):
        self.fade_out.update(current_time_ms)
        for i, box in enumerate(self.boxes):
            is_selected = i == self.selected_box_index
            box.update(current_time_ms, is_selected)

    def draw(self):
        for box in self.boxes:
            box.draw(self.fade_out.attribute)
