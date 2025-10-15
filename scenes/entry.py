import pyray as ray

from libs.audio import audio
from libs.chara_2d import Chara2D
from libs.global_objects import AllNetIcon, CoinOverlay, Nameplate, Indicator, EntryOverlay, Timer
from libs.texture import tex
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
)


class State:
    SELECT_SIDE = 0
    SELECT_MODE = 1

class EntryScreen:
    def __init__(self):
        self.screen_init = False

    def on_screen_start(self):
        if not self.screen_init:
            tex.load_screen_textures('entry')
            audio.load_screen_sounds('entry')
            self.side = 1
            self.box_manager = BoxManager()
            self.state = State.SELECT_SIDE
            plate_info = global_data.config['nameplate']
            self.nameplate = Nameplate(plate_info['name'], plate_info['title'], -1, -1, False)
            self.indicator = Indicator(Indicator.State.SELECT)
            self.coin_overlay = CoinOverlay()
            self.allnet_indicator = AllNetIcon()
            self.entry_overlay = EntryOverlay()
            self.timer = Timer(60, get_current_ms(), self.box_manager.select_box)
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
            self.nameplate_fadein = tex.get_animation(12)
            self.side_select_fade.start()
            self.chara = Chara2D(0, 100)
            self.announce_played = False
            audio.play_sound('bgm', 'music')

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        audio.stop_sound('bgm')
        self.nameplate.unload()
        tex.unload_textures()
        audio.unload_all_sounds()
        audio.unload_all_music()
        return next_screen

    def handle_input(self):
        if self.box_manager.is_box_selected():
            return
        if self.state == State.SELECT_SIDE:
            if is_l_don_pressed() or is_r_don_pressed():
                if self.side == 1:
                    return self.on_screen_end("TITLE")
                global_data.player_num = round((self.side/3) + 1)
                self.drum_move_1.start()
                self.drum_move_2.start()
                self.drum_move_3.start()
                self.cloud_resize.start()
                self.cloud_resize_loop.start()
                self.cloud_texture_change.start()
                self.cloud_fade.start()
                audio.play_sound('cloud', 'sound')
                audio.play_sound(f'entry_start_{global_data.player_num}p', 'voice')
                plate_info = global_data.config['nameplate']
                self.nameplate.unload()
                self.nameplate = Nameplate(plate_info['name'], plate_info['title'], global_data.player_num, plate_info['dan'], plate_info['gold'])
                self.nameplate_fadein.start()
                self.state = State.SELECT_MODE
                if self.side == 2:
                    self.chara = Chara2D(1, 100)
                else:
                    self.chara = Chara2D(0, 100)
                audio.play_sound('don', 'sound')
            if is_l_kat_pressed():
                audio.play_sound('kat', 'sound')
                self.side = max(0, self.side - 1)
            if is_r_kat_pressed():
                audio.play_sound('kat', 'sound')
                self.side = min(2, self.side + 1)
        elif self.state == State.SELECT_MODE:
            if is_l_don_pressed() or is_r_don_pressed():
                audio.play_sound('don', 'sound')
                self.box_manager.select_box()
            if is_l_kat_pressed():
                audio.play_sound('kat', 'sound')
                self.box_manager.move_left()
            if is_r_kat_pressed():
                audio.play_sound('kat', 'sound')
                self.box_manager.move_right()

    def update(self):
        self.on_screen_start()
        current_time = get_current_ms()
        self.side_select_fade.update(current_time)
        self.bg_flicker.update(current_time)
        self.drum_move_1.update(current_time)
        self.drum_move_2.update(current_time)
        self.drum_move_3.update(current_time)
        self.cloud_resize.update(current_time)
        self.cloud_texture_change.update(current_time)
        self.cloud_fade.update(current_time)
        self.cloud_resize_loop.update(current_time)
        self.box_manager.update(current_time)
        self.nameplate_fadein.update(current_time)
        self.nameplate.update(current_time)
        self.indicator.update(current_time)
        self.timer.update(current_time)
        self.chara.update(current_time, 100, False, False)
        if self.box_manager.is_finished():
            return self.on_screen_end(self.box_manager.selected_box())
        if self.cloud_fade.is_finished and not audio.is_sound_playing(f'entry_start_{global_data.player_num}p') and not self.announce_played:
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

    def draw_footer(self):
        tex.draw_texture('side_select', 'footer')
        if self.state == State.SELECT_SIDE or self.side != 0:
            tex.draw_texture('side_select', 'footer_left')
        if self.state == State.SELECT_SIDE or self.side != 2:
            tex.draw_texture('side_select', 'footer_right')

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

        self.chara.draw(480, 240)

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
        self.nameplate.draw(500, 185)

    def draw_player_drum(self):
        move_x = self.drum_move_3.attribute
        move_y = self.drum_move_1.attribute + self.drum_move_2.attribute
        if self.side == 0:
            offset = 0
            tex.draw_texture('side_select', 'red_drum', x=move_x, y=move_y)
        else:
            move_x *= -1
            offset = 620
            tex.draw_texture('side_select', 'blue_drum', x=move_x, y=move_y)

        scale = self.cloud_resize.attribute
        if self.cloud_resize.is_finished:
            scale = max(1, self.cloud_resize_loop.attribute)
        if self.side == 2:
            self.chara.draw(move_x + offset + 130, 570 + move_y, mirror=True)
        else:
            self.chara.draw(move_x + offset + 170, 570 + move_y)
        tex.draw_texture('side_select', 'cloud', x=move_x + offset, y=move_y, frame=self.cloud_texture_change.attribute, fade=self.cloud_fade.attribute, scale=scale, center=True)

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

        if self.state == State.SELECT_MODE:
            if self.side == 0:
                self.nameplate.draw(30, 640, fade=self.nameplate_fadein.attribute)
                self.indicator.draw(50, 575, fade=self.nameplate_fadein.attribute)
            else:
                self.nameplate.draw(950, 640, fade=self.nameplate_fadein.attribute)
                self.indicator.draw(770, 575, fade=self.nameplate_fadein.attribute)

        tex.draw_texture('global', 'player_entry')

        if self.box_manager.is_finished():
            ray.draw_rectangle(0, 0, 1280, 720, ray.BLACK)

        self.timer.draw()
        self.entry_overlay.draw(y=-10)
        self.coin_overlay.draw()
        self.allnet_indicator.draw()

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
        self.x = self.box_tex_obj.x[0]
        self.y = self.box_tex_obj.y[0]
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
        if isinstance(texture_left, list):
            raise Exception("highlight textures cannot be iterable")
        tex.draw_texture('mode_select', 'box_highlight_center', x=self.left_x + texture_left.width, y=self.y, x2=self.right_x - self.left_x -15, color=color)
        tex.draw_texture('mode_select', 'box_highlight_left', x=self.left_x, y=self.y, color=color)
        tex.draw_texture('mode_select', 'box_highlight_right', x=self.right_x, y=self.y, color=color)

    def _draw_text(self, color):
        text_x = self.x + (self.texture.width//2) - (self.text.texture.width//2)
        if self.is_selected:
            text_x += self.open.attribute
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
