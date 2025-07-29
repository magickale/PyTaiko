from pathlib import Path

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.utils import (
    OutlinedText,
    draw_scaled_texture,
    get_current_ms,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
    load_all_textures_from_zip,
    load_texture_from_zip,
)


class State:
    SELECT_SIDE = 0
    SELECT_MODE = 1

class EntryScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.screen_init = False
        self.box_titles: list[tuple[OutlinedText, OutlinedText]] = [(OutlinedText('演奏ゲーム', 50, ray.WHITE, ray.Color(109, 68, 24, 255), outline_thickness=5, vertical=True),
        OutlinedText('演奏ゲーム', 50, ray.WHITE, ray.BLACK, outline_thickness=5, vertical=True)),
        (OutlinedText('ゲーム設定', 50, ray.WHITE, ray.Color(109, 68, 24, 255), outline_thickness=5, vertical=True),
        OutlinedText('ゲーム設定', 50, ray.WHITE, ray.BLACK, outline_thickness=5, vertical=True))]

    def load_textures(self):
        self.textures = load_all_textures_from_zip(Path('Graphics/lumendata/entry.zip'))
        self.texture_black = load_texture_from_zip(Path('Graphics/lumendata/attract/movie.zip'), 'movie_img00000.png')

    def unload_textures(self):
        for group in self.textures:
            for texture in self.textures[group]:
                ray.unload_texture(texture)

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
            self.selected_box = 0
            self.num_boxes = 2
            self.state = State.SELECT_SIDE
            self.screen_init = True
            self.drum_move_1 = None
            self.drum_move_2 = None
            self.drum_move_3 = None
            self.cloud_resize = None
            self.cloud_texture_change = None
            self.cloud_fade = None
            self.fade_out = None
            self.cloud_resize_loop = Animation.create_texture_resize(200, initial_size=1.0, final_size=1.1, reverse_delay=200)
            self.side_select_fade = Animation.create_fade(100, initial_opacity=0.0, final_opacity=1.0)
            self.bg_flicker = Animation.create_fade(500, initial_opacity=0.5, final_opacity=0.4, reverse_delay=0)
            audio.play_sound(self.bgm)

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        self.unload_textures()
        audio.stop_sound(self.bgm)
        return next_screen

    def handle_input(self):
        if self.fade_out is not None:
            return
        if self.state == State.SELECT_SIDE:
            if is_l_don_pressed() or is_r_don_pressed():
                if self.side == 1:
                    return self.on_screen_end("TITLE")
                self.drum_move_1 = Animation.create_move(350, total_distance=-295, ease_out='quadratic')
                self.drum_move_2 = Animation.create_move(200, total_distance=50, delay=self.drum_move_1.duration, ease_in='quadratic')
                self.drum_move_3 = Animation.create_move(350, total_distance=-170, delay=self.drum_move_1.duration+self.drum_move_2.duration, ease_out='quadratic')
                self.cloud_resize = Animation.create_texture_resize(350, initial_size=0.75, final_size=1.0)
                self.cloud_resize_loop = Animation.create_texture_resize(200, initial_size=1.0, final_size=1.2, reverse_delay=200, delay=self.cloud_resize.duration)
                textures = ((0, 83.35, 45), (83.35, 166.7, 48), (166.7, 250, 49), (250, 333, 50))
                self.cloud_texture_change = Animation.create_texture_change(333, textures=textures, delay=self.drum_move_1.duration+self.drum_move_2.duration+self.drum_move_3.duration)
                self.cloud_fade = Animation.create_fade(83.35, delay=self.drum_move_1.duration+self.drum_move_2.duration+self.drum_move_3.duration+self.cloud_texture_change.duration)
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
                self.fade_out = Animation.create_fade(160)
            if is_l_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.selected_box = max(0, self.selected_box - 1)
            if is_r_kat_pressed():
                audio.play_sound(self.sound_kat)
                self.selected_box = min(self.num_boxes - 1, self.selected_box + 1)

    def update(self):
        self.on_screen_start()
        self.side_select_fade.update(get_current_ms())
        self.bg_flicker.update(get_current_ms())
        if self.bg_flicker.is_finished:
            self.bg_flicker.restart()
        if self.drum_move_1 is not None:
            self.drum_move_1.update(get_current_ms())
        if self.drum_move_2 is not None:
            self.drum_move_2.update(get_current_ms())
        if self.drum_move_3 is not None:
            self.drum_move_3.update(get_current_ms())
        if self.cloud_resize is not None:
            self.cloud_resize.update(get_current_ms())
        if self.cloud_texture_change is not None:
            self.cloud_texture_change.update(get_current_ms())
        if self.cloud_fade is not None:
            self.cloud_fade.update(get_current_ms())
        self.cloud_resize_loop.update(get_current_ms())
        if self.cloud_resize_loop.is_finished:
            self.cloud_resize_loop = Animation.create_texture_resize(200, initial_size=1.0, final_size=1.1, reverse_delay=200)
        if self.fade_out is not None:
            self.fade_out.update(get_current_ms())
            if self.fade_out.is_finished:
                if self.selected_box == 0:
                    return self.on_screen_end("SONG_SELECT")
                elif self.selected_box == 1:
                    return self.on_screen_end("SETTINGS")
        return self.handle_input()

    def draw_background(self):
        bg_texture = self.textures['entry'][368]
        src = ray.Rectangle(0, 0, bg_texture.width, bg_texture.height)
        dest = ray.Rectangle(0, 0, self.width, bg_texture.height)
        ray.draw_texture_pro(bg_texture, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

        ray.draw_texture(self.textures['entry'][369], (self.width // 2) - (self.textures['entry'][369].width // 2), (self.height // 2) - self.textures['entry'][369].height, ray.WHITE)
        ray.draw_texture(self.textures['entry'][370], 0, (self.height // 2) - (self.textures['entry'][370].height // 2), ray.WHITE)
        ray.draw_texture(self.textures['entry'][371], (self.width // 2) - (self.textures['entry'][371].width // 2), (self.height // 2) - (self.textures['entry'][371].height // 2) + 10, ray.WHITE)
        ray.draw_texture(self.textures['entry'][372], 0, 0, ray.WHITE)
        ray.draw_texture(self.textures['entry'][373], self.width - self.textures['entry'][373].width, 0, ray.WHITE)
        draw_scaled_texture(self.textures['entry'][374], -7, -15, 2.0, ray.fade(ray.WHITE, self.bg_flicker.attribute))

    def draw_footer(self):
        ray.draw_texture(self.textures['entry'][375], 1, self.height - self.textures['entry'][375].height + 7, ray.WHITE)
        if self.state == State.SELECT_SIDE or self.side != 0:
            ray.draw_texture(self.textures['entry'][376], 1, self.height - self.textures['entry'][376].height + 1, ray.WHITE)
        if self.state == State.SELECT_SIDE or self.side != 2:
            ray.draw_texture(self.textures['entry'][377], 2 + self.textures['entry'][377].width, self.height - self.textures['entry'][376].height + 1, ray.WHITE)

    def draw_side_select(self, fade):
        color = ray.fade(ray.WHITE, fade)
        left_x, top_y, right_x, bottom_y = 238, 108, 979, 520
        ray.draw_texture(self.textures['entry'][205], left_x, top_y, color)
        ray.draw_texture(self.textures['entry'][208], right_x, top_y, color)
        ray.draw_texture(self.textures['entry'][204], left_x, bottom_y, color)
        ray.draw_texture(self.textures['entry'][207], right_x, bottom_y, color)

        texture = self.textures['entry'][209]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(left_x + self.textures['entry'][205].width, top_y, right_x - left_x - (self.textures['entry'][205].width), texture.height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, color)
        texture = self.textures['entry'][210]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(left_x + self.textures['entry'][205].width, bottom_y, right_x - left_x - (self.textures['entry'][205].width), texture.height)
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, color)

        texture = self.textures['entry'][203]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(left_x, top_y + self.textures['entry'][205].height, texture.width, bottom_y - top_y - (self.textures['entry'][205].height))
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, color)
        texture = self.textures['entry'][206]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(right_x, top_y + self.textures['entry'][205].height, texture.width, bottom_y - top_y - (self.textures['entry'][205].height))
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, color)

        texture = self.textures['entry'][202]
        src = ray.Rectangle(0, 0, texture.width, texture.height)
        dest = ray.Rectangle(left_x + self.textures['entry'][205].width, top_y + self.textures['entry'][205].height, right_x - left_x - (self.textures['entry'][205].width), bottom_y - top_y - (self.textures['entry'][205].height))
        ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, color)

        ray.draw_texture(self.textures['entry'][226], 384, 144, color)

        cursor_x = 261
        cursor_texture = self.textures['entry'][230]
        flip = 1
        if self.side == 0:
            texture = self.textures['entry'][229]
            flip = -1
        else:
            texture = self.textures['entry'][232]
        ray.draw_texture(texture, 261, 400, color)

        if self.side == 1:
            texture = self.textures['entry'][76]
            cursor_texture = self.textures['entry'][77]
            cursor_x = 512
        else:
            texture = self.textures['entry'][228]
        ray.draw_texture(texture, 512, 400, color)
        ray.draw_texture(self.textures['entry'][201], 512, 408, color)

        if self.side == 2:
            texture = self.textures['entry'][233]
            cursor_x = 762
        else:
            texture = self.textures['entry'][227]
        ray.draw_texture(texture, 762, 400, color)

        src = ray.Rectangle(0, 0, cursor_texture.width * flip, cursor_texture.height)
        dest = ray.Rectangle(cursor_x, 400, cursor_texture.width, cursor_texture.height)
        ray.draw_texture_pro(cursor_texture, src, dest, ray.Vector2(0, 0), 0, color)

    def draw_player_drum(self):
        move_x = 0
        if self.drum_move_3 is not None:
            move_x = int(self.drum_move_3.attribute)
        if self.side == 0:
            drum_texture = self.textures['entry'][366]
            x = 160
        else:
            drum_texture = self.textures['entry'][367]
            x = 780
            move_x = move_x * -1
        move_y = 0
        if self.drum_move_1 is not None:
            move_y = int(self.drum_move_1.attribute)
            if self.drum_move_2 is not None:
                move_y += int(self.drum_move_2.attribute)
        ray.draw_texture(drum_texture, x + move_x, 720 + move_y, ray.WHITE)
        if self.cloud_resize is not None and not self.cloud_resize.is_finished:
            scale = self.cloud_resize.attribute
        else:
            scale = max(1, self.cloud_resize_loop.attribute)
        texture_index = 45
        if self.cloud_texture_change is not None and self.cloud_texture_change.attribute != 0:
            texture_index = self.cloud_texture_change.attribute
        color = ray.fade(ray.WHITE, 1.0)
        if self.cloud_fade is not None:
            color = ray.fade(ray.WHITE, self.cloud_fade.attribute)
        draw_scaled_texture(self.textures['entry'][texture_index], x + move_x - int(160 * (scale-1)), 720 + move_y - 200 - int(160 * (scale-1)), scale, color)

    def draw_mode_select(self, fade):
        self.draw_player_drum()
        color = ray.fade(ray.WHITE, fade)
        if self.cloud_fade is not None and self.cloud_fade.is_finished:
            box_width = self.textures['entry'][262].width
            spacing = 80
            push_distance = 50
            total_width = self.num_boxes * box_width + (self.num_boxes - 1) * spacing
            start_x = self.width//2 - total_width//2
            y = self.height//2 - (self.textures['entry'][262].height//2) - 15
            for i in range(self.num_boxes):
                x_pos = start_x + i * (box_width + spacing)
                push_offset = 0
                if i != self.selected_box:
                    if i < self.selected_box:
                        push_offset = -push_distance
                    else:
                        push_offset = push_distance
                final_x = x_pos + push_offset
                ray.draw_texture(self.textures['entry'][262], final_x, y, color)
                if i == self.selected_box:
                    ray.draw_texture(self.textures['entry'][302], final_x, y, color)
                    texture = self.textures['entry'][304]
                    src = ray.Rectangle(0, 0, texture.width, texture.height)
                    dest = ray.Rectangle(final_x + self.textures['entry'][302].width, y, 100 - self.textures['entry'][302].width, texture.height)
                    ray.draw_texture_pro(texture, src, dest, ray.Vector2(0, 0), 0, color)
                    ray.draw_texture(self.textures['entry'][303], final_x+100, y, color)

                    box_title = self.box_titles[i][1]
                    src = ray.Rectangle(0, 0, box_title.texture.width, box_title.texture.height)
                    dest = ray.Rectangle(final_x + 25, y + 20, box_title.texture.width, box_title.texture.height)
                    box_title.draw(src, dest, ray.Vector2(0, 0), 0, color)
                else:
                    box_title = self.box_titles[i][0]
                    src = ray.Rectangle(0, 0, box_title.texture.width, box_title.texture.height)
                    dest = ray.Rectangle(final_x + 20, y + 20, box_title.texture.width, box_title.texture.height)
                    box_title.draw(src, dest, ray.Vector2(0, 0), 0, color)

    def draw(self):
        self.draw_background()
        if self.state == State.SELECT_SIDE:
            self.draw_side_select(self.side_select_fade.attribute)
        elif self.state == State.SELECT_MODE:
            if self.fade_out is not None:
                self.draw_mode_select(self.fade_out.attribute)
            else:
                self.draw_mode_select(1.0)
        self.draw_footer()

        ray.draw_texture(self.textures['entry'][320], 0, 0, ray.WHITE)

        if self.fade_out is not None and self.fade_out.is_finished:
            src = ray.Rectangle(0, 0, self.texture_black.width, self.texture_black.height)
            dest = ray.Rectangle(0, 0, self.width, self.height)
            ray.draw_texture_pro(self.texture_black, src, dest, ray.Vector2(0, 0), 0, ray.WHITE)

    def draw_3d(self):
        pass
