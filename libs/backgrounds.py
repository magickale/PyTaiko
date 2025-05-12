import random
from pathlib import Path

import pyray as ray

from libs.animation import Animation
from libs.utils import load_all_textures_from_zip

'''
class Background:
    class Chibi:
        def __init__(self):
            self.texture_index = Animation.create_texture_change(249, textures=[(0, 150, 4), (150, 183, 0), (183, 183 + 33, 1), (183 + 33, 183 + 66, 2)])
            self.chibi_color = 5
            self.move = Animation.create_move(1000, total_distance=1280)
        def update(self):
            self.chibi_color = random.choice([5, 10, 15, 20])
            self.texture_index.update(get_current_ms())
            self.move.update(get_current_ms())
            if self.texture_index.is_finished:
                self.texture_index = Animation.create_texture_change(100, textures=[(0, 150, 4), (150, 183, 0), (183, 183 + 33, 1), (183 + 33, 183 + 66, 2)])
        def draw(self, textures):
            ray.draw_texture(textures[self.texture_index.attribute + self.chibi_color], 200 + int(self.move.attribute), 0, ray.WHITE)

    def __init__(self, width: int, height: int):
        self.screen_width = width
        self.screen_height = height
        self.bg_fever_name = 'bg_fever_a_' + str(random.randint(1, 4)).zfill(2)
        self.bg_normal_name = 'bg_nomal_a_' + str(random.randint(1, 5)).zfill(2)
        self.chibi_name = 'chibi_a_' + str(random.randint(1, 14)).zfill(2)
        self.dance_name = 'dance_a_' + str(random.randint(1, 22)).zfill(2)
        self.donbg_name = 'donbg_a_' + str(random.randint(1, 6)).zfill(2)
        self.fever_name = 'fever_a_' + str(random.randint(1, 4)).zfill(2)
        self.renda_name = 'renda_a_' + str(random.randint(1, 3)).zfill(2)

        self.textures = dict()

        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.bg_fever_name}.zip')))
        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.bg_normal_name}.zip')))
        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.chibi_name}.zip')))
        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.dance_name}.zip')))
        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.donbg_name}_1p.zip')))
        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.donbg_name}_2p.zip')))
        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.fever_name}.zip')))
        self.textures.update(load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.renda_name}.zip')))

        self.donbg_move = Animation.create_move(2500, start_position=0, total_distance=-self.textures[self.donbg_name + '_1p'][0].width)

        self.chibis = []

    def update(self):
        self.donbg_move.update(get_current_ms())
        if self.donbg_move.is_finished:
            self.donbg_move = Animation.create_move(2500, start_position=0, total_distance=-self.textures[self.donbg_name + '_1p'][0].width)
        for chibi in self.chibis:
            chibi.update()
            if chibi.move.is_finished:
                self.chibis.remove(chibi)
    def draw(self):
        ray.draw_texture(self.textures[self.bg_normal_name][0], 0, 360, ray.WHITE)
        ray.draw_texture(self.textures[self.bg_normal_name][1], 0, 360, ray.fade(ray.WHITE, 0.25))

        # for chibi in self.chibis:
        #     chibi.draw(self.textures[self.chibi_name])
'''

class Background:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.donbg = DonBG.create(self.screen_width, self.screen_height, random.randint(6, 6), 1)
        self.bg_normal = BGNormal.create(self.screen_width, self.screen_height, 1)
        self.bg_fever = BGFever.create(self.screen_width, self.screen_height, 4)
        self.footer = Footer(self.screen_width, self.screen_height, random.randint(1, 3))
        self.is_clear = False
    def update(self, current_time_ms: float, is_clear: bool):
        self.is_clear = is_clear
        self.donbg.update(current_time_ms, is_clear)
        self.bg_normal.update(current_time_ms)
        self.bg_fever.update(current_time_ms)
    def draw(self):
        self.bg_normal.draw()
        if self.is_clear:
            self.bg_fever.draw()
        self.footer.draw()
        self.donbg.draw()

class DonBG:

    @staticmethod
    def create(screen_width: int, screen_height: int, index: int, player_num: int):
        map = [None, DonBG1, DonBG1, DonBG1, DonBG1, DonBG1, DonBG6]
        selected_obj = map[index]
        return selected_obj(index, screen_width, screen_height, player_num)

class DonBGBase:
    def __init__(self, index: int, screen_width: int, screen_height: int, player_num: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.player_num = player_num
        self.name = 'donbg_a_' + str(index).zfill(2)
        self.textures = (load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.name}_{self.player_num}p.zip')))
        self.move = Animation.create_move(3000, start_position=0, total_distance=-self.textures[self.name + f'_{self.player_num}p'][0].width)
        self.is_clear = False

    def update(self, current_time_ms: float, is_clear: bool):
        self.is_clear = is_clear
        self.move.update(current_time_ms)
        if self.move.is_finished:
            self.move = Animation.create_move(3000, start_position=0, total_distance=-self.textures[self.name + f'_{self.player_num}p'][0].width)

class DonBG1(DonBGBase):
    def __init__(self, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(index, screen_width, screen_height, player_num)
        self.overlay_move = Animation.create_move(1000, start_position=0, total_distance=20, reverse_delay=0)
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
        if self.overlay_move.is_finished:
            self.overlay_move = Animation.create_move(1000, start_position=0, total_distance=20, reverse_delay=0)
    def draw(self):
        texture_index = 0
        if self.is_clear:
            texture_index = 2
        top_texture = self.textures[self.name + f'_{self.player_num}p'][0 + texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, ray.WHITE)

        texture = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i + int(self.move.attribute), int(self.overlay_move.attribute) - 50, ray.WHITE)

class DonBG6(DonBGBase):
    def __init__(self, index: int, screen_width: int, screen_height: int, player_num: int):
        super().__init__(index, screen_width, screen_height, player_num)
        self.overlay_move = Animation.create_move(1000, start_position=0, total_distance=20, reverse_delay=0)
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
        if self.overlay_move.is_finished:
            self.overlay_move = Animation.create_move(1000, start_position=0, total_distance=20, reverse_delay=0)
    def draw(self):
        texture_index = 0
        if self.is_clear:
            texture_index = 3
        top_texture = self.textures[self.name + f'_{self.player_num}p'][0 + texture_index]
        for i in range(0, self.screen_width + top_texture.width, top_texture.width):
            ray.draw_texture(top_texture, i + int(self.move.attribute), 0, ray.WHITE)

        texture_flowers = self.textures[self.name + f'_{self.player_num}p'][1 + texture_index]
        for i in range(0, self.screen_width, texture_flowers.width):
            if i % (2 * texture_flowers.width) != 0:
                ray.draw_texture(texture_flowers, i + int(self.move.attribute*3) + 100, -int(self.move.attribute*0.85)-100, ray.WHITE)

        texture = self.textures[self.name + f'_{self.player_num}p'][2 + texture_index]
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i + int(self.move.attribute), int(self.overlay_move.attribute) - 50, ray.WHITE)

class BGNormal:

    @staticmethod
    def create(screen_width: int, screen_height: int, index: int):
        map = [None, BGNormal1]
        selected_obj = map[index]
        return selected_obj(index, screen_width, screen_height)

class BGNormalBase:
    def __init__(self, index: int, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.name = 'bg_nomal_a_' + str(index).zfill(2)
        self.textures = (load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.name}.zip')))

class BGNormal1(BGNormalBase):
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
        self.flicker = Animation.create_fade(16.67*2, initial_opacity=0.5, final_opacity=0.25, reverse_delay=0)
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
        if self.flicker.is_finished:
            self.flicker = Animation.create_fade(16.67*2, initial_opacity=0.5, final_opacity=0.25, reverse_delay=0)
    def draw(self):
        ray.draw_texture(self.textures[self.name][0], 0, 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][1], 0, 360, ray.fade(ray.WHITE, self.flicker.attribute))

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
        self.vertical_move = Animation.create_move(1300, start_position=0, total_distance=50, reverse_delay=0)
        self.horizontal_move = Animation.create_move(5000, start_position=0, total_distance=self.textures[self.name][2].width)

class BGFever4(BGFeverBase):
    def __init__(self, index: int, screen_width: int, screen_height: int):
        super().__init__(index, screen_width, screen_height)
    def update(self, current_time_ms: float):
        self.vertical_move.update(current_time_ms)
        if self.vertical_move.is_finished:
            self.vertical_move = Animation.create_move(1300, start_position=0, total_distance=50, reverse_delay=0)
        self.horizontal_move.update(current_time_ms)
        if self.horizontal_move.is_finished:
            self.horizontal_move = Animation.create_move(5000, start_position=0, total_distance=self.textures[self.name][2].width)
    def draw(self):
        texture = self.textures[self.name][0]
        for i in range(0, self.screen_width + texture.width, texture.width):
            ray.draw_texture(texture, i, 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][1], 0, 360 + 50 - int(self.vertical_move.attribute), ray.WHITE)
        ray.draw_texture(self.textures[self.name][2], -int(self.horizontal_move.attribute), 360, ray.WHITE)
        ray.draw_texture(self.textures[self.name][2], self.textures[self.name][2].width -int(self.horizontal_move.attribute), 360, ray.WHITE)

class Footer:
    def __init__(self, screen_width: int, screen_height: int, index: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.name = 'dodai_a_' + str(index).zfill(2)
        self.textures = (load_all_textures_from_zip(Path(f'Graphics/lumendata/enso_original/{self.name}.zip')))
    def draw(self):
        ray.draw_texture(self.textures[self.name][0], 0, self.screen_height - self.textures[self.name][0].height + 20, ray.WHITE)
