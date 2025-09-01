import random

from libs.animation import Animation
from libs.texture import TextureWrapper


class Background:
    def __init__(self, player_num: int):
        self.tex_wrapper = TextureWrapper()
        self.tex_wrapper.load_animations('background')
        self.donbg = DonBG.create(self.tex_wrapper, random.randint(0, 5), player_num)
        self.bg_normal = BGNormal.create(self.tex_wrapper, random.randint(0, 4))
        self.bg_fever = BGFever.create(self.tex_wrapper, 3)
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
        self.bg_normal.draw(self.tex_wrapper)
        if self.is_clear:
            self.bg_fever.draw(self.tex_wrapper)
        self.footer.draw(self.tex_wrapper)
        self.donbg.draw(self.tex_wrapper)

    def unload(self):
        self.tex_wrapper.unload_textures()

class DonBG:

    @staticmethod
    def create(tex: TextureWrapper, index: int, player_num: int):
        map = [DonBG1, DonBG2, DonBG3, DonBG4, DonBG5, DonBG6]
        selected_obj = map[index]
        return selected_obj(tex, index, player_num)

class DonBGBase:
    def __init__(self, tex: TextureWrapper, index: int, player_num: int):
        self.name = f'{index}_{player_num}'
        tex.load_zip('background', f'donbg/{self.name}')
        self.move = tex.get_animation(0)
        self.is_clear = False
        self.clear_fade = tex.get_animation(1)

    def update(self, current_time_ms: float, is_clear: bool):
        if not self.is_clear and is_clear:
            self.clear_fade.start()
        self.is_clear = is_clear
        self.move.update(current_time_ms)
        self.clear_fade.update(current_time_ms)

class DonBG1(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: int):
        super().__init__(tex, index, player_num)
        self.overlay_move = tex.get_animation(2)
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        self._draw_textures(tex, 1.0)
        if self.is_clear:
            self._draw_textures(tex, self.clear_fade.attribute)
    def _draw_textures(self, tex: TextureWrapper, fade: float):
        for i in range(5):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute)
        for i in range(6):
            tex.draw_texture(self.name, 'overlay', frame=self.is_clear, fade=fade, x=(i*347)+self.move.attribute*(347/328), y=self.overlay_move.attribute)
        for i in range(30):
            tex.draw_texture(self.name, 'footer', frame=self.is_clear, fade=fade, x=(i*56)+self.move.attribute*((56/328)*3), y=self.overlay_move.attribute)

class DonBG2(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: int):
        super().__init__(tex, index, player_num)
        self.overlay_move = tex.get_animation(3)
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        self._draw_textures(tex, 1.0)
        if self.is_clear:
            self._draw_textures(tex, self.clear_fade.attribute)
    def _draw_textures(self, tex: TextureWrapper, fade: float):
        for i in range(5):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute)
            tex.draw_texture(self.name, 'overlay', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute, y=self.overlay_move.attribute)

class DonBG3(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: int):
        super().__init__(tex, index, player_num)
        self.bounce_up = tex.get_animation(4)
        self.bounce_down = tex.get_animation(5)
        self.bounce_up.start()
        self.bounce_down.start()
        self.overlay_move = tex.get_animation(6)
        self.overlay_move_2 = tex.get_animation(7)

    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.bounce_up.update(current_time_ms)
        self.bounce_down.update(current_time_ms)
        if self.bounce_down.is_finished:
            self.bounce_up.restart()
            self.bounce_down.restart()
        self.overlay_move.update(current_time_ms)
        self.overlay_move_2.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        self._draw_textures(tex, 1.0)
        if self.is_clear:
            self._draw_textures(tex, self.clear_fade.attribute)

    def _draw_textures(self, tex: TextureWrapper, fade: float):
        for i in range(10):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*164)+self.move.attribute)
        y = self.bounce_up.attribute - self.bounce_down.attribute + self.overlay_move.attribute + self.overlay_move_2.attribute
        for i in range(6):
            tex.draw_texture(self.name, 'overlay', frame=self.is_clear, fade=fade, x=(i*328)+(self.move.attribute*2), y=y)

class DonBG4(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: int):
        super().__init__(tex, index, player_num)
        self.overlay_move = tex.get_animation(2)
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        self._draw_textures(tex, 1.0)
        if self.is_clear:
            self._draw_textures(tex, self.clear_fade.attribute)

    def _draw_textures(self, tex: TextureWrapper, fade: float):
        for i in range(5):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute)
            tex.draw_texture(self.name, 'overlay', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute, y=self.overlay_move.attribute)

class DonBG5(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: int):
        super().__init__(tex, index, player_num)
        self.bounce_up = tex.get_animation(4)
        self.bounce_down = tex.get_animation(5)
        self.bounce_up.start()
        self.bounce_down.start()
        self.adjust = tex.get_animation(8)

    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.bounce_up.update(current_time_ms)
        self.bounce_down.update(current_time_ms)
        if self.bounce_down.is_finished:
            self.bounce_up.restart()
            self.bounce_down.restart()
        self.adjust.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        self._draw_textures(tex, 1.0)
        if self.is_clear:
            self._draw_textures(tex, self.clear_fade.attribute)

    def _draw_textures(self, tex: TextureWrapper, fade: float):
        for i in range(5):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute)
        for i in range(6):
            tex.draw_texture(self.name, 'overlay', frame=self.is_clear, fade=fade, x=(i*368)+(self.move.attribute * ((184/328)*2)), y=self.bounce_up.attribute - self.bounce_down.attribute - self.adjust.attribute)

class DonBG6(DonBGBase):
    def __init__(self, tex: TextureWrapper, index: int, player_num: int):
        super().__init__(tex, index, player_num)
        self.overlay_move = tex.get_animation(2)
    def update(self, current_time_ms: float, is_clear: bool):
        super().update(current_time_ms, is_clear)
        self.overlay_move.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        self._draw_textures(tex, 1.0)
        if self.is_clear:
            self._draw_textures(tex, self.clear_fade.attribute)

    def _draw_textures(self, tex: TextureWrapper, fade: float):
        for i in range(5):
            tex.draw_texture(self.name, 'background', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute)
        for i in range(0, 6, 2):
            tex.draw_texture(self.name, 'overlay_1', frame=self.is_clear, fade=fade, x=(i*264) + self.move.attribute*3, y=-self.move.attribute*0.85)
        for i in range(5):
            tex.draw_texture(self.name, 'overlay_2', frame=self.is_clear, fade=fade, x=(i*328)+self.move.attribute, y=self.overlay_move.attribute)

class BGNormal:

    @staticmethod
    def create(tex: TextureWrapper, index: int):
        map = [BGNormal1, BGNormal2, BGNormal3, BGNormal4, BGNormal5]
        selected_obj = map[index]
        return selected_obj(tex, index)

class BGNormalBase:
    def __init__(self, tex: TextureWrapper, index: int):
        self.name = "bg_" + str(index)
        tex.load_zip('background', f'bg_normal/{self.name}')

class BGNormal1(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(9)
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'overlay', fade=self.flicker.attribute)

class BGNormal2(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(9)
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'overlay', fade=self.flicker.attribute)

class BGNormal3(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(10)
    def update(self, current_time_ms):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'center')
        tex.draw_texture(self.name, 'overlay')

        tex.draw_texture(self.name, 'lamps', index=0)
        tex.draw_texture(self.name, 'lamps', index=1, mirror='horizontal')

        tex.draw_texture(self.name, 'light_orange', index=0, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_orange', index=1, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_red', fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_green', fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_orange', index=2, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_yellow', index=0, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_yellow', index=1, fade=self.flicker.attribute)

        tex.draw_texture(self.name, 'side_l')
        tex.draw_texture(self.name, 'side_l_2')
        tex.draw_texture(self.name, 'side_r')

class BGNormal4(BGNormalBase):
    class Petal:
        def __init__(self):
            self.spawn_point = self.random_excluding_range()
            duration = random.randint(1400, 2000)
            self.move_x = Animation.create_move(duration, total_distance=random.randint(-300, 300))
            self.move_y = Animation.create_move(duration, total_distance=360)
            self.move_x.start()
            self.move_y.start()
        def random_excluding_range(self):
            while True:
                num = random.randint(0, 1280)
                if num < 260 or num > 540:
                    return num
        def update(self, current_time_ms):
            self.move_x.update(current_time_ms)
            self.move_y.update(current_time_ms)
        def draw(self, name: str, tex: TextureWrapper):
            tex.draw_texture(name, 'petal', x=self.spawn_point + self.move_x.attribute, y=360+self.move_y.attribute, fade=0.75)
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(11)
        self.turtle_move = tex.get_animation(12)
        self.turtle_change = tex.get_animation(13)
        self.petals = {self.Petal(), self.Petal(), self.Petal(), self.Petal(), self.Petal()}
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
        self.turtle_move.update(current_time_ms)
        self.turtle_change.update(current_time_ms)
        for petal in self.petals:
            petal.update(current_time_ms)
            if petal.move_y.is_finished:
                self.petals.remove(petal)
                self.petals.add(self.Petal())
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')
        tex.draw_texture(self.name, 'chara')
        tex.draw_texture(self.name, 'turtle', frame=self.turtle_change.attribute, x=self.turtle_move.attribute)

        tex.draw_texture(self.name, 'overlay')

        for petal in self.petals:
            petal.draw(self.name, tex)

class BGNormal5(BGNormalBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.flicker = tex.get_animation(14)
    def update(self, current_time_ms: float):
        self.flicker.update(current_time_ms)
    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background')

        tex.draw_texture(self.name, 'paper_lamp', frame=9, index=0)
        tex.draw_texture(self.name, 'paper_lamp', frame=8, index=1)
        tex.draw_texture(self.name, 'paper_lamp', frame=7, index=2)
        tex.draw_texture(self.name, 'paper_lamp', frame=6, index=3)
        tex.draw_texture(self.name, 'paper_lamp', frame=5, index=4)
        tex.draw_texture(self.name, 'paper_lamp', frame=4, index=5)
        tex.draw_texture(self.name, 'paper_lamp', frame=3, index=6)
        tex.draw_texture(self.name, 'paper_lamp', frame=2, index=7)
        tex.draw_texture(self.name, 'paper_lamp', frame=1, index=8)
        tex.draw_texture(self.name, 'paper_lamp', frame=0, index=9)

        tex.draw_texture(self.name, 'light_overlay', index=0, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=1, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=2, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=3, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=4, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=5, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=6, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=7, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=8, fade=self.flicker.attribute)
        tex.draw_texture(self.name, 'light_overlay', index=9, fade=self.flicker.attribute)

        tex.draw_texture(self.name, 'overlay', fade=0.75)

        tex.draw_texture(self.name, 'lamp_overlay', index=0, fade=0.75)
        tex.draw_texture(self.name, 'lamp_overlay', index=1, fade=0.75)
        tex.draw_texture(self.name, 'lamp', index=0)
        tex.draw_texture(self.name, 'lamp', index=1)

class BGFever:

    @staticmethod
    def create(tex: TextureWrapper, index: int):
        map = [BGFever1, BGFever2, None, BGFever4]
        selected_obj = map[index]
        return selected_obj(tex, index)

class BGFeverBase:
    def __init__(self, tex: TextureWrapper, index: int):
        self.name = 'bg_fever_' + str(index)
        tex.load_zip('background', f'bg_fever/{self.name}')
        self.transitioned = False

class BGFever1(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        pass

    def start(self):
        pass

    def update(self, current_time_ms: float):
        pass

    def draw(self, tex: TextureWrapper):
        pass

class BGFever2(BGFeverBase):
    def __init__(self, tex: TextureWrapper, index: int):
        super().__init__(tex, index)
        self.fadein = tex.get_animation(19)
        self.bg_texture_change = tex.get_animation(20)
        self.ship_rotation = Animation.create_fade(1000, initial_opacity=0.0, final_opacity=1.0, reverse_delay=0, loop=True)
        self.ship_rotation.start()

    def start(self):
        self.fadein.start()

    def update(self, current_time_ms: float):
        self.fadein.update(current_time_ms)
        self.bg_texture_change.update(current_time_ms)
        self.ship_rotation.update(current_time_ms)

    def draw(self, tex: TextureWrapper):
        tex.draw_texture(self.name, 'background', frame=self.bg_texture_change.attribute, fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'footer_3', fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'footer_1', fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'footer_2', fade=self.fadein.attribute)
        tex.draw_texture(self.name, 'bird', index=0, mirror='horizontal')
        tex.draw_texture(self.name, 'bird', index=1)
        tex.draw_texture(self.name, 'ship', rotation=self.ship_rotation.attribute*100, center=True)

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

class Footer:
    def __init__(self, tex: TextureWrapper, index: int):
        self.index = index
        tex.load_zip('background', 'footer')
    def draw(self, tex: TextureWrapper):
        tex.draw_texture('footer', str(self.index))
