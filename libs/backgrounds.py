import random
from pathlib import Path

import pyray as ray

from libs.animation import Animation
from libs.texture import TextureWrapper
from libs.utils import load_all_textures_from_zip


class Background:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.tex_wrapper = TextureWrapper()
        self.tex_wrapper.load_animations('background')
        self.donbg = DonBG.create(self.tex_wrapper, self.screen_width, self.screen_height, random.randint(1, 6), 1)
        self.bg_normal = BGNormal.create(self.screen_width, self.screen_height, random.randint(1, 5))
        self.bg_fever = BGFever.create(self.screen_width, self.screen_height, 4)
        self.footer = Footer(self.tex_wrapper, random.randint(0, 2))
        self.is_clear = False
    def update(self, current_time_ms: float, is_clear: bool):
        if not self.is_clear and is_clear:
            self.bg_fever.start()
        self.is_clear = is_clear
        self.donbg.update(current_time_ms, self.is_clear)
        self.bg_normal.update(current_time_ms)
        self.bg_fever.update(current_time_ms)
    def draw(self):
        self.bg_normal.draw()
        if self.is_clear:
            self.bg_fever.draw()
        self.footer.draw(self.tex_wrapper)
        self.donbg.draw()

    def unload(self):
        self.donbg.unload()
        self.bg_normal.unload()
        self.bg_fever.unload()

class DonBG:

    @staticmethod
    def create(tex: TextureWrapper, screen_width: int, screen_height: int, index: int, player_num: int):
        map = [None, DonBG1, DonBG2, DonBG3, DonBG4, DonBG5, DonBG6]
        selected_obj = map[index]
        return selected_obj(tex, index, screen_width, screen_height, player_num)

class DonBGBase:
    def __init__(self, tex: TextureWrapper, index: int, screen_width: int, screen_height: int, player_num: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        #tex.load_zip('background', f'donbg/{index}_{player_num}')
        self.player_num = player_num
        self.name = 'donbg_a_' + str(index).zfill(2)
        self.textures = (load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.name}_{self.player_num}p.zip')))
        self.move = Animation.create_move(3000, start_position=0, total_distance=-self.textures[self.name + f'_{self.player_num}p'][0].width)
        self.move.start()
        self.is_clear = False
        self.clear_fade = None

    def update(self, current_time_ms: float, is_clear: bool):
        if not self.is_clear and is_clear:
            self.clear_fade = Animation.create_fade(150, initial_opacity=0.0, final_opacity=1.0)
            self.clear_fade.start()
        self.is_clear = is_clear
        self.move.update(current_time_ms)
        if self.clear_fade is not None:
            self.clear_fade.update(current_time_ms)
        if self.move.is_finished:
            self.move.restart()

    def unload(self):
        for texture_group in self.textures:
            for texture in self.textures[texture_group]:
                ray.unload_texture(texture)

class DonBG1(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(tex, index, screen_width, screen_height, player_num)
        self.overlay_move = Animation.create_move(1000, start_position=0, total_distance=20, reverse_delay=0)
        self.overlay_move.start()
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
        if self.overlay_move.is_finished:
            self.overlay_move.restart()
    def draw(self):
        self._draw_textures(0, ray.WHITE)
        if self.is_clear and self.clear_fade is not None:
            self._draw_textures(3, ray.fade(ray.WHITE, self.clear_fade.attribute))
    def _draw_textures(self, texture_index: int, color: ray.Color):
        top_texture = self.textures[self.name + f'_{self.player_num}p'][0 + texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, color)

        wave_texture = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width + (wave_texture.width+80), wave_texture.width+80):
            ray.draw_texture(wave_texture, i + int(self.move.attribute * ((wave_texture.width+80)/top_texture.width)) + 100, int(self.overlay_move.attribute), color)

        texture = self.textures[self.name + f'_{self.player_num}p'][2 + texture_index]
        for i in range(0, self.screen_width + texture.width + texture.width*5, texture.width):
            ray.draw_texture(texture, i + int(self.move.attribute * (texture.width/top_texture.width)*3), int(self.overlay_move.attribute) + 105, color)

class DonBG2(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(tex, index, screen_width, screen_height, player_num)
        self.overlay_move = Animation.create_move(1500, start_position=0, total_distance=20, reverse_delay=0)
        self.overlay_move.start()
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
        if self.overlay_move.is_finished:
            self.overlay_move.restart()
    def draw(self):
        self._draw_textures(0, ray.WHITE)
        if self.is_clear and self.clear_fade is not None:
            self._draw_textures(2, ray.fade(ray.WHITE, self.clear_fade.attribute))
    def _draw_textures(self, texture_index: int, color: ray.Color):
        top_texture = self.textures[self.name + f'_{self.player_num}p'][texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, color)

        texture = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i + int(self.move.attribute), int(self.overlay_move.attribute) - 25, color)

class DonBG3(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(tex, index, screen_width, screen_height, player_num)
        duration = 266
        bounce_distance = 40
        self.bounce_up = Animation.create_move(duration, total_distance=-bounce_distance, ease_out='quadratic')
        self.bounce_up.start()
        self.bounce_down = Animation.create_move(duration, total_distance=-bounce_distance, ease_in='quadratic', delay=self.bounce_up.duration)
        self.bounce_down.start()
        self.overlay_move = Animation.create_move(duration*3, total_distance=20, reverse_delay=0, ease_in='quadratic', ease_out='quadratic', delay=self.bounce_up.duration+self.bounce_down.duration)
        self.overlay_move.start()
        self.overlay_move_2 = Animation.create_move(duration*3, total_distance=20, reverse_delay=0, ease_in='quadratic', ease_out='quadratic', delay=self.bounce_up.duration+self.bounce_down.duration+self.overlay_move.duration)
        self.overlay_move_2.start()

    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.bounce_up.update(current_time_ms)
        self.bounce_down.update(current_time_ms)
        self.overlay_move.update(current_time_ms)
        self.overlay_move_2.update(current_time_ms)
        if self.overlay_move_2.is_finished:
            self.bounce_up.restart()
            self.bounce_down.restart()
            self.overlay_move.restart()
            self.overlay_move_2.restart()

    def draw(self):
        self._draw_textures(0, ray.WHITE)
        if self.is_clear and self.clear_fade is not None:
            self._draw_textures(2, ray.fade(ray.WHITE, self.clear_fade.attribute))

    def _draw_textures(self, texture_index: int, color: ray.Color):
        top_texture = self.textures[self.name + f'_{self.player_num}p'][0 + texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, color)
        texture = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i + int(self.move.attribute*2), int(self.bounce_up.attribute) - int(self.bounce_down.attribute) - 25 + int(self.overlay_move.attribute) + int(self.overlay_move_2.attribute), color)

class DonBG4(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(tex, index, screen_width, screen_height, player_num)
        self.overlay_move = Animation.create_move(1500, start_position=0, total_distance=20, reverse_delay=0)
        self.overlay_move.start()
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
        if self.overlay_move.is_finished:
            self.overlay_move.restart()
    def draw(self):
        self._draw_textures(0, ray.WHITE)
        if self.is_clear and self.clear_fade is not None:
            self._draw_textures(2, ray.fade(ray.WHITE, self.clear_fade.attribute))

    def _draw_textures(self, texture_index: int, color: ray.Color):
        top_texture = self.textures[self.name + f'_{self.player_num}p'][texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, color)

        texture = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i + int(self.move.attribute), int(self.overlay_move.attribute) - 25, color)

class DonBG5(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(tex, index, screen_width, screen_height, player_num)
        duration = 266
        bounce_distance = 40
        self.bounce_up = Animation.create_move(duration, total_distance=-bounce_distance, ease_out='quadratic')
        self.bounce_up.start()
        self.bounce_down = Animation.create_move(duration, total_distance=-bounce_distance, ease_in='quadratic', delay=self.bounce_up.duration)
        self.bounce_down.start()
        self.adjust = Animation.create_move(1000, total_distance=10, reverse_delay=0, delay=self.bounce_up.duration+self.bounce_down.duration)
        self.adjust.start()

    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.bounce_up.update(current_time_ms)
        self.bounce_down.update(current_time_ms)
        self.adjust.update(current_time_ms)
        if self.adjust.is_finished:
            self.bounce_up.restart()
            self.bounce_down.restart()
            self.adjust.restart()

    def draw(self):
        self._draw_textures(0, ray.WHITE)
        if self.is_clear and self.clear_fade is not None:
            self._draw_textures(2, ray.fade(ray.WHITE, self.clear_fade.attribute))

    def _draw_textures(self, texture_index: int, color: ray.Color):
        top_texture = self.textures[self.name + f'_{self.player_num}p'][0 + texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, color)
        texture = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width + texture.width + texture.width*2, texture.width*2):
            ray.draw_texture(texture, i + int((self.move.attribute * (texture.width/top_texture.width))*2), int(self.bounce_up.attribute) - int(self.bounce_down.attribute) - int(self.adjust.attribute), color)

class DonBG6(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(tex, index, screen_width, screen_height, player_num)
        self.overlay_move = Animation.create_move(1000, start_position=0, total_distance=20, reverse_delay=0)
        self.overlay_move.start()
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
        if self.overlay_move.is_finished:
            self.overlay_move.restart()
    def draw(self):
        self._draw_textures(0, ray.WHITE)
        if self.is_clear and self.clear_fade is not None:
            self._draw_textures(3, ray.fade(ray.WHITE, self.clear_fade.attribute))

    def _draw_textures(self, texture_index: int, color: ray.Color):
        top_texture = self.textures[self.name + f'_{self.player_num}p'][0 + texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, color)

        texture_flowers = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width, texture_flowers.width):
            if i % (2 * texture_flowers.width) != 0:
                ray.draw_texture(texture_flowers, i + int(self.move.attribute*3) + 100, -int(self.move.attribute*0.85)-100, color)

        texture = self.textures[self.name + f'_{self.player_num}p'][2 + texture_index]
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i + int(self.move.attribute), int(self.overlay_move.attribute) - 50, color)

class BGNormal:

    @staticmethod
    def create(screen_width: int, screen_height: int, index: int):
        map = [None, BGNormal1, BGNormal2, BGNormal3, BGNormal4, BGNormal5]
        selected_obj = map[index]
        return selected_obj(index, screen_width, screen_height)

class BGNormalBase:
    def __init__(self, index: int, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.name = 'bg_nomal_a_' + str(index).zfill(2)
        self.textures = (load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.name}.zip')))

    def unload(self):
        for texture_group in self.textures:
            for texture in self.textures[texture_group]:
                ray.unload_texture(texture)

class BGNormal1(BGNormalBase):
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
        self.flicker = Animation.create_fade(16.67*4, initial_opacity=0.5, final_opacity=0.4, reverse_delay=0)
        self.flicker.start()
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
        if self.flicker.is_finished:
            self.flicker.restart()
    def draw(self):
        ray.draw_texture(self.textures[self.name][0], 0, 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][1], 0, 360, ray.fade(ray.WHITE, self.flicker.attribute))

class BGNormal2(BGNormalBase):
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
        self.flicker = Animation.create_fade(16.67*4, initial_opacity=0.5, final_opacity=0.4, reverse_delay=0)
        self.flicker.start()
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
        if self.flicker.is_finished:
            self.flicker.restart()
    def draw(self):
        ray.draw_texture(self.textures[self.name][0], 0, 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][1], 0, 360, ray.fade(ray.WHITE, self.flicker.attribute))

class BGNormal3(BGNormalBase):
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
        self.flicker = Animation.create_fade(16.67*10, initial_opacity=0.5, final_opacity=0.4, reverse_delay=0)
        self.flicker.start()
    def update(self, current_time_ms):
        self.flicker.update(current_time_ms)
        if self.flicker.is_finished:
            self.flicker.restart()
    def draw(self):
        src = ray.Rectangle(0, 0, self.textures[self.name][0].width, self.textures[self.name][0].height)
        dest = ray.Rectangle(0, 360, self.screen_width, self.textures[self.name][0].height)
        ray.draw_texture_pro(self.textures[self.name][0], src, dest, ray.Vector2(0, 0), 0, ray.WHITE)
        ray.draw_texture(self.textures[self.name][3], (self.screen_width//2) - (self.textures[self.name][3].width//2), 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][6], 0, 360, ray.WHITE)

        src = ray.Rectangle(0, 0, -self.textures[self.name][7].width, self.textures[self.name][7].height)
        dest = ray.Rectangle((self.screen_width//2) - 170, 490, self.textures[self.name][7].width, self.textures[self.name][7].height)
        ray.draw_texture_pro(self.textures[self.name][7], src, dest, ray.Vector2(0, 0), 0, ray.WHITE)
        ray.draw_texture(self.textures[self.name][7], (self.screen_width//2) + 50, 490, ray.WHITE)


        #Orange
        color = ray.fade(ray.WHITE, self.flicker.attribute)
        ray.draw_texture(self.textures[self.name][1], (self.screen_width//2) + 180, 300, color)
        ray.draw_texture(self.textures[self.name][1], (self.screen_width//2) - 380, 300, color)

        #Red Green Orange
        ray.draw_texture(self.textures[self.name][2], (self.screen_width//2) - 220, 350, color)
        ray.draw_texture(self.textures[self.name][4], (self.screen_width//2) - 100, 350, color)
        ray.draw_texture(self.textures[self.name][1], (self.screen_width//2) + 10, 350, color)

        #Yellow
        ray.draw_texture(self.textures[self.name][5], (self.screen_width//2) - 220, 500, color)
        ray.draw_texture(self.textures[self.name][5], (self.screen_width//2) + 10, 500, color)

        ray.draw_texture(self.textures[self.name][9], (self.screen_width//2) - 320, 520, ray.WHITE)
        ray.draw_texture(self.textures[self.name][10], 100, 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][11], self.screen_width - 100 - self.textures[self.name][11].width, 360, ray.WHITE)

class BGNormal4(BGNormalBase):
    class Petal:
        def __init__(self):
            self.spawn_point = self.random_excluding_range()
            duration = random.randint(1400, 2000)
            self.move_y = Animation.create_move(duration, total_distance=360)
            self.move_y.start()
            self.move_x = Animation.create_move(duration, total_distance=random.randint(-300, 300))
            self.move_x.start()
        def random_excluding_range(self):
            while True:
                num = random.randint(0, 1280)
                if num < 260 or num > 540:
                    return num
        def update(self, current_time_ms):
            self.move_x.update(current_time_ms)
            self.move_y.update(current_time_ms)
        def draw(self, texture):
            ray.draw_texture(texture, self.spawn_point + int(self.move_x.attribute), 360+int(self.move_y.attribute), ray.fade(ray.WHITE, 0.75))
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
        self.flicker = Animation.create_fade(16.67*3, initial_opacity=0.5, final_opacity=0.4, reverse_delay=0)
        self.flicker.start()
        self.turtle_move = Animation.create_move(3333*2, start_position=screen_width+112, total_distance=-(screen_width+(112*4)))
        self.turtle_move.start()
        textures = ((0, 100, 3), (100, 200, 4), (200, 300, 5), (300, 400, 6), (400, 500, 7), (500, 600, 8))
        self.turtle_change = Animation.create_texture_change(600, textures=textures)
        self.turtle_change.start()
        self.petals = {self.Petal(), self.Petal(), self.Petal(), self.Petal(), self.Petal()}
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
        if self.flicker.is_finished:
            self.flicker.restart()
        self.turtle_move.update(current_time_ms)
        if self.turtle_move.is_finished:
            self.turtle_move.restart()
        self.turtle_change.update(current_time_ms)
        if self.turtle_change.is_finished:
            self.turtle_change.restart()
        for petal in self.petals:
            petal.update(current_time_ms)
            if petal.move_y.is_finished:
                self.petals.remove(petal)
                self.petals.add(self.Petal())
    def draw(self):
        ray.draw_texture(self.textures[self.name][0], 0, 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][2], self.screen_width//2 - 20, 380, ray.WHITE)
        ray.draw_texture(self.textures[self.name][self.turtle_change.attribute], int(self.turtle_move.attribute), 550, ray.WHITE)

        ray.draw_texture(self.textures[self.name][9], 0, 360, ray.WHITE)

        for petal in self.petals:
            petal.draw(self.textures[self.name][10])

class BGNormal5(BGNormalBase):
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
        self.flicker = Animation.create_fade(16.67*10, initial_opacity=0.75, final_opacity=0.4, reverse_delay=0)
        self.flicker.start()
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
        if self.flicker.is_finished:
            self.flicker.restart()
    def draw(self):
        ray.draw_texture(self.textures[self.name][0], 0, 360, ray.WHITE)

        ray.draw_texture(self.textures[self.name][13], -35, 340, ray.WHITE)
        ray.draw_texture(self.textures[self.name][12], 103, 380, ray.WHITE)
        ray.draw_texture(self.textures[self.name][11], 241, 400, ray.WHITE)
        ray.draw_texture(self.textures[self.name][10], 380, 380, ray.WHITE)
        ray.draw_texture(self.textures[self.name][9], 518, 340, ray.WHITE)
        ray.draw_texture(self.textures[self.name][4], 657, 340, ray.WHITE)
        ray.draw_texture(self.textures[self.name][5], 795, 380, ray.WHITE)
        ray.draw_texture(self.textures[self.name][6], 934, 400, ray.WHITE)
        ray.draw_texture(self.textures[self.name][7], 1072, 380, ray.WHITE)
        ray.draw_texture(self.textures[self.name][8], 1211, 340, ray.WHITE)

        color = ray.fade(ray.WHITE, self.flicker.attribute)
        ray.draw_texture(self.textures[self.name][14], -35 - 10, 340 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 103 - 10, 380 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 241 - 10, 400 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 380 - 10, 380 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 518 - 10, 340 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 657 - 10, 340 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 795 - 10, 380 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 934 - 10, 400 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 1072 - 10, 380 - 10, color)
        ray.draw_texture(self.textures[self.name][14], 1211 - 10, 340 - 10, color)

        ray.draw_texture(self.textures[self.name][3], (self.screen_width//2) - (self.textures[self.name][3].width//2), 360+172, ray.fade(ray.WHITE, 0.75))

        ray.draw_texture(self.textures[self.name][1], 50, 600, ray.fade(ray.WHITE, 0.75))
        ray.draw_texture(self.textures[self.name][1], self.screen_width-50 - self.textures[self.name][2].width, 600, ray.fade(ray.WHITE, 0.75))
        ray.draw_texture(self.textures[self.name][2], self.screen_width-50 - self.textures[self.name][2].width, 600, ray.WHITE)
        ray.draw_texture(self.textures[self.name][2], 50, 600, ray.WHITE)

class BGFever:

    @staticmethod
    def create(screen_width: int, screen_height: int, index: int):
        map = [None, None, None, None, BGFever4]
        selected_obj = map[index]
        return selected_obj(index, screen_width, screen_height)

class BGFeverBase:
    def __init__(self, index: int, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.name = 'bg_fever_a_' + str(index).zfill(2)
        self.textures = (load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.name}.zip')))
        self.transitioned = False

    def unload(self):
        for texture_group in self.textures:
            for texture in self.textures[texture_group]:
                ray.unload_texture(texture)

class BGFever4(BGFeverBase):
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
        self.vertical_move = Animation.create_move(1300, start_position=0, total_distance=50, reverse_delay=0)
        self.vertical_move.start()
        self.horizontal_move = Animation.create_move(5000, start_position=0, total_distance=self.textures[self.name][2].width)
        self.horizontal_move.start()
        self.bg_texture_move_down = None
        self.bg_texture_move_up = None

    def start(self):
        self.bg_texture_move_down = Animation.create_move(516, total_distance=400, ease_in='cubic')
        self.bg_texture_move_down.start()
        self.bg_texture_move_up = Animation.create_move(200, total_distance=40, delay=self.bg_texture_move_down.duration, ease_out='quadratic')
        self.bg_texture_move_up.start()

    def update(self, current_time_ms: float):
        if self.bg_texture_move_down is not None:
            self.bg_texture_move_down.update(current_time_ms)

        if self.bg_texture_move_up is not None:
            self.bg_texture_move_up.update(current_time_ms)
            if self.bg_texture_move_up.is_finished and not self.transitioned:
                self.transitioned = True
                self.vertical_move.restart()
                self.horizontal_move.restart()

        if self.transitioned:
            self.vertical_move.update(current_time_ms)
            if self.vertical_move.is_finished:
                self.vertical_move.restart()
            self.horizontal_move.update(current_time_ms)
            if self.horizontal_move.is_finished:
                self.horizontal_move.restart()
    def draw(self):
        if self.bg_texture_move_down is None or self.bg_texture_move_up is None:
            return
        texture = self.textures[self.name][0]
        y = int(self.bg_texture_move_down.attribute) - int(self.bg_texture_move_up.attribute)
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i, y, ray.WHITE)
        ray.draw_texture(self.textures[self.name][1], 0, (720 + 50 - int(self.vertical_move.attribute)) - y, ray.WHITE)
        ray.draw_texture(self.textures[self.name][2], -int(self.horizontal_move.attribute), y, ray.WHITE)
        ray.draw_texture(self.textures[self.name][2], self.textures[self.name][2].width -int(self.horizontal_move.attribute), y, ray.WHITE)

class Footer:
    def __init__(self, tex: TextureWrapper, index: int):
        self.index = index
        tex.load_zip('background', 'footer')
    def draw(self, tex: TextureWrapper):
        tex.draw_texture('footer', str(self.index))
