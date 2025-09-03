import math

import pyray as ray

from libs.animation import Animation
from libs.texture import TextureWrapper


class BGFever:

    @staticmethod
    def create(tex: TextureWrapper, index: int):
        map = [BGFever1, BGFever2, BGFever3, BGFever4]
        selected_obj = map[index]
        return selected_obj(tex, index)

class BGFeverBase:
    def __init__(self, tex: TextureWrapper, index: int):
        self.name = 'bg_fever_' + str(index)
        tex.load_zip('background', f'bg_fever/{self.name}')
        self.transitioned = False

class BGFever1(BGFeverBase):
    class Tile:
        def __init__(self):
            self.expansion = Animation.create_move(166, total_distance=360)
            self.expansion.start()
        def update(self, current_time_ms):
            self.expansion.update(current_time_ms)
        def draw(self, tex: TextureWrapper, name: str, x: int, frame: int):
            tex.draw_texture(name, 'background', frame=frame, x=x, y2=-360+self.expansion.attribute, y=360+(180-self.expansion.attribute/2))
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.wait = 0
        self.bg_tiles: list[BGFever1.Tile] = []
        self.corner_move_up = tex.get_animation(29)
        self.corner_move_down = tex.get_animation(30)
        self.footer_move_up = tex.get_animation(29, is_copy=True)
        self.footer_move_down = tex.get_animation(30, is_copy=True)
        self.footer_move_up.delay_saved = 100
        self.footer_move_down.delay_saved = 100

        self.mountain_move_up = tex.get_animation(29, is_copy=True)
        self.mountain_move_down = tex.get_animation(30, is_copy=True)
        self.mountain_move_up.delay_saved = 200
        self.mountain_move_down.delay_saved = 200

        self.overlay_move_up = tex.get_animation(29, is_copy=True)
        self.overlay_move_down = tex.get_animation(30, is_copy=True)
        self.overlay_move_up.delay_saved = 300
        self.overlay_move_down.delay_saved = 300

        self.wave_spin = tex.get_animation(28)
        self.circle = {
            "center_x": 100,
            "center_y": 130,
            "radius": 200,
        }
        self.bg_move = tex.get_animation(16)

    def start(self):
        self.corner_move_up.start()
        self.corner_move_down.start()
        self.footer_move_up.start()
        self.footer_move_down.start()
        self.mountain_move_up.start()
        self.mountain_move_down.start()
        self.overlay_move_up.start()
        self.overlay_move_down.start()

    def update(self, current_time_ms: float):
        if len(self.bg_tiles) < 20 and current_time_ms >= self.wait + 66:
            self.bg_tiles.append(BGFever1.Tile())
            self.wait = current_time_ms
        for tile in self.bg_tiles:
            tile.update(current_time_ms)
        self.corner_move_up.update(current_time_ms)
        self.corner_move_down.update(current_time_ms)
        self.footer_move_up.update(current_time_ms)
        self.footer_move_down.update(current_time_ms)
        self.mountain_move_up.update(current_time_ms)
        self.mountain_move_down.update(current_time_ms)
        self.overlay_move_up.update(current_time_ms)
        self.overlay_move_down.update(current_time_ms)
        self.wave_spin.update(current_time_ms)
        if (self.overlay_move_down.is_finished and len(self.bg_tiles) == 20) and not self.is_transitioned:
            self.bg_move.restart()
        self.is_transitioned = self.overlay_move_down.is_finished and len(self.bg_tiles) == 20
        if self.is_transitioned:
            self.bg_move.update(current_time_ms)


    def draw(self, tex: TextureWrapper):
        for i, tile in enumerate(self.bg_tiles):
            tile.draw(tex, self.name, (i*128)-self.bg_move.attribute, i % 10)
        tex.draw_texture(self.name, 'mountain', y=-self.mountain_move_up.attribute+self.mountain_move_down.attribute)
        angle = math.radians(self.wave_spin.attribute*2)
        wave_x = self.circle["center_x"] + math.cos(angle) * self.circle["radius"]
        wave_y = self.circle["center_y"] + math.sin(angle) * self.circle["radius"]
        wave_origin = ray.Vector2(tex.textures[self.name]['wave'].width/2,tex.textures[self.name]['wave'].height/2)
        tex.draw_texture(self.name, 'wave', x=wave_x, y=wave_y, origin=wave_origin)
        tex.draw_texture(self.name, 'footer', y=-self.footer_move_up.attribute+self.footer_move_down.attribute)
        tex.draw_texture(self.name, 'corner', y=-self.corner_move_up.attribute+self.corner_move_down.attribute)
        tex.draw_texture(self.name, 'overlay', y=self.overlay_move_up.attribute-self.overlay_move_down.attribute)

class BGFever2(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.fadein = tex.get_animation(19)
        self.bg_texture_change = tex.get_animation(20)
        self.ship_rotation = tex.get_animation(21)
        self.ship_rotation.start()
        self.move_in = tex.get_animation(22)
        self.move_out = tex.get_animation(23)

    def start(self):
        self.fadein.start()
        self.move_in.start()
        self.move_out.start()

    def update(self, current_time_ms: float):
        self.fadein.update(current_time_ms)
        self.bg_texture_change.update(current_time_ms)
        self.ship_rotation.update(current_time_ms)
        self.move_in.update(current_time_ms)
        self.move_out.update(current_time_ms)
        self.transitioned = self.move_out.is_finished

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background', frame=self.bg_texture_change.attribute, fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'footer_3', y=self.move_in.attribute-self.move_out.attribute, fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'footer_1', y=self.move_in.attribute-self.move_out.attribute, fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'footer_2', y=self.move_in.attribute-self.move_out.attribute, fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'bird', index=0, x=self.move_in.attribute-self.move_out.attribute, mirror='horizontal', y=self.ship_rotation.attribute*180)
        tex.draw_texture(self.name, 'bird', index=1, x=-self.move_in.attribute+self.move_out.attribute, y=self.ship_rotation.attribute*180)
        origin = ray.Vector2(tex.textures[self.name]['ship'].width/2, tex.textures[self.name]['ship'].height/2)
        tex.draw_texture(self.name, 'ship', x=origin.x, y=origin.y + self.move_in.attribute-self.move_out.attribute, origin=origin, rotation=self.ship_rotation.attribute*100, center=True)

class BGFever3(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.fadein = tex.get_animation(19)
        self.move_in = tex.get_animation(24)
        self.footer_move_up = tex.get_animation(26)
        self.bird_tc = tex.get_animation(20)
        self.overlay_tc = tex.get_animation(25)
        self.circle_rotate = tex.get_animation(27)
        self.fish_spin = tex.get_animation(28)

        self.circle = {
            "center_x": 500,
            "center_y": 300,
            "radius": 300,
        }

        self.num_fish = 8
        self.fish_spacing = (2 * math.pi) / self.num_fish  # 45 degrees in radians

    def start(self):
        self.fadein.start()
        self.move_in.start()
        self.footer_move_up.start()

    def update(self, current_time_ms: float):
        self.fadein.update(current_time_ms)
        self.move_in.update(current_time_ms)
        self.bird_tc.update(current_time_ms)
        self.overlay_tc.update(current_time_ms)
        self.footer_move_up.update(current_time_ms)
        self.circle_rotate.update(current_time_ms)
        self.fish_spin.update(current_time_ms)
        self.transitioned = self.move_in.is_finished

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background', x=-self.move_in.attribute)
        tex.draw_texture(self.name, 'overlay', frame=self.overlay_tc.attribute, fade=self.fadein.attribute)
        origin = ray.Vector2(tex.textures[self.name]['circle'].width/2, tex.textures[self.name]['circle'].height/2)
        tex.draw_texture(self.name, 'circle', x=origin.x, y=origin.y, fade=self.fadein.attribute, origin=origin, rotation=self.circle_rotate.attribute)

        angle = math.radians(self.fish_spin.attribute*2)
        wave_x = self.circle["center_x"] + math.cos(angle) * self.circle["radius"]
        wave_y = self.circle["center_y"] + math.sin(angle) * self.circle["radius"]
        wave_origin = ray.Vector2(tex.textures[self.name]['wave'].width/2,tex.textures[self.name]['wave'].height/2)
        tex.draw_texture(self.name, 'wave', x=wave_x, y=wave_y, fade=self.fadein.attribute, origin=wave_origin)

        for j in range(2):
            for i in range(self.num_fish):
                fish_phase_offset = i * self.fish_spacing
                angle = math.radians(self.fish_spin.attribute) + fish_phase_offset
                fish_x = self.circle["center_x"] + math.cos(angle) * self.circle["radius"]
                fish_y = self.circle["center_y"] + math.sin(angle) * self.circle["radius"]

                # Fish should face the direction they're swimming (tangent to circle)
                swimming_angle = angle + math.pi/2  # Perpendicular to radius
                swimming_rotation = math.degrees(swimming_angle)

                fish_origin = ray.Vector2(tex.textures[self.name]['fish'].width/2,tex.textures[self.name]['fish'].height/2)

                tex.draw_texture(self.name, 'fish', x=fish_x, y=fish_y, fade=self.fadein.attribute,
                    origin=fish_origin,
                    rotation=swimming_rotation,
                    index=j
                )

        angle = math.radians(self.fish_spin.attribute*3)
        wave_x = self.circle["center_x"] + math.cos(angle) * 20
        wave_y = self.circle["center_y"] + math.sin(angle) * 20
        wave_origin = ray.Vector2(tex.textures[self.name]['wave'].width/2,tex.textures[self.name]['wave'].height/2)
        for i in range(3):
            tex.draw_texture(self.name, 'footer_2', x=wave_x + (i*600), y=wave_y, fade=self.fadein.attribute, origin=wave_origin)

        for i in range(3):
            tex.draw_texture(self.name, 'footer_1', x=i*450, y=-self.footer_move_up.attribute)
        tex.draw_texture(self.name, 'bird', frame=self.bird_tc.attribute, index=0, x=-self.move_in.attribute)
        tex.draw_texture(self.name, 'bird', frame=self.bird_tc.attribute, index=1, x=-self.move_in.attribute)

class BGFever4(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.vertical_move = tex.get_animation(15)
        self.horizontal_move = tex.get_animation(16)
        self.bg_texture_move_down = tex.get_animation(17)
        self.bg_texture_move_up = tex.get_animation(18)

    def start(self):
        self.bg_texture_move_down.start()
        self.bg_texture_move_up.start()

    def update(self, current_time_ms: float):
        self.bg_texture_move_down.update(current_time_ms)

        self.bg_texture_move_up.update(current_time_ms)
        if self.bg_texture_move_up.is_finished and not self.transitioned:
            self.transitioned = True
            self.vertical_move.restart()
            self.horizontal_move.restart()

        if self.transitioned:
            self.vertical_move.update(current_time_ms)
            self.horizontal_move.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        y = self.bg_texture_move_down.attribute - self.bg_texture_move_up.attribute
        for i in range(0, 1384, 104):
            tex.draw_texture(self.name, 'background', x=i, y=y)
        tex.draw_texture(self.name, 'overlay_1', y=-self.vertical_move.attribute - y)
        tex.draw_texture(self.name, 'overlay_2', x=-self.horizontal_move.attribute, y=y)
        tex.draw_texture(self.name, 'overlay_2', x=1256 - self.horizontal_move.attribute, y=y)
