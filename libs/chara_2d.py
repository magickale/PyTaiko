import logging
from libs.animation import Animation
from libs.utils import global_tex

logger = logging.getLogger(__name__)

class Chara2D:
    def __init__(self, index: int, bpm: float = 100, path: str = 'chara'):
        """
        Initialize a Chara2D object.

        Args:
            index (int): The index of the character.
            bpm (float): The beats per minute.
            path (str, optional): The path to the character's textures. Defaults to 'chara'.
        """
        self.name = "chara_" + str(index)
        self.tex = global_tex
        self.anims = dict()
        self.bpm = bpm
        self.current_anim = 'normal'
        self.past_anim = 'normal'
        self.is_rainbow = False
        self.is_clear = False
        self.is_gogo = False
        self.temp_anims = {'10_combo','10_combo_max', 'soul_in', 'clear_in', 'balloon_pop', 'balloon_miss', 'gogo_start'}
        for name in self.tex.textures[self.name]:
            tex_list = self.tex.textures[self.name][name].texture
            keyframe_len = len(tex_list) if isinstance(tex_list, list) else 1
            if index == 0:
                duration = 2250*2 / self.bpm
            else:
                duration = 2250 / self.bpm
            total_duration = duration * keyframe_len
            keyframes = [i for i in range(keyframe_len)]
            textures = [[duration*i, duration*(i+1), index] for i, index in enumerate(keyframes)]
            self.anims[name] = Animation.create_texture_change(total_duration, textures=textures)
            self.anims[name].start()
        logger.info(f"Chara2D initialized: index={index}, bpm={bpm}, path={path}")

    def set_animation(self, name: str):
        """
        Set the current animation for the character.

        Args:
            name (str): The name of the animation to set.
        """
        if name == self.current_anim:
            return
        if self.current_anim in self.temp_anims:
            return
        if self.is_gogo and name == '10_combo':
            return
        self.past_anim = self.current_anim
        if name == 'balloon_pop' or name == 'balloon_miss' or name == 'gogo_stop':
            self.past_anim = 'normal'
            if self.is_clear:
                self.past_anim = 'clear'
            if self.is_gogo:
                self.past_anim = 'gogo'
            if name == 'gogo_stop':
                name = self.past_anim
                self.is_gogo = False
        elif name == 'gogo_start':
            self.is_gogo = True
            self.past_anim = 'gogo'
        self.current_anim = name
        self.anims[name].start()
        logger.debug(f"Animation set: {name}")
    def update(self, current_time_ms: float, bpm: float = 100, is_clear: bool = False, is_rainbow: bool = False):
        """
        Update the character's animation state and appearance.

        Args:
            current_time_ms (float): The current time in milliseconds.
            bpm (float): The beats per minute.
            is_clear (bool): Whether the gauge is in clear mode.
            is_rainbow (bool): Whether the gauge is in rainbow mode.
        """
        if is_rainbow and not self.is_rainbow:
            self.is_rainbow = True
            self.set_animation('soul_in')
            logger.info("Rainbow state entered, soul_in animation triggered")
        if is_clear and not self.is_clear:
            self.is_clear = True
            self.set_animation('clear_in')
            self.past_anim = 'clear'
            logger.info("Clear state entered, clear_in animation triggered")
        if bpm != self.bpm:
            self.bpm = bpm
            for name in self.tex.textures[self.name]:
                tex_list = self.tex.textures[self.name][name].texture
                keyframe_len = len(tex_list) if isinstance(tex_list, list) else 1
                duration = 2250 / self.bpm
                total_duration = duration * keyframe_len
                keyframes = [i for i in range(keyframe_len)]
                textures = [[duration*i, duration*(i+1), index] for i, index in enumerate(keyframes)]
                self.anims[name] = Animation.create_texture_change(total_duration, textures=textures)
                self.anims[name].start()
            logger.info(f"BPM changed, animations updated: bpm={bpm}")
        self.anims[self.current_anim] = self.anims[self.current_anim]
        self.anims[self.current_anim].update(current_time_ms)
        if self.anims[self.current_anim].is_finished:
            if self.current_anim in self.temp_anims:
                self.anims[self.current_anim].reset()
                self.current_anim = self.past_anim
            self.anims[self.current_anim].restart()

    def draw(self, x: float = 0, y: float = 0, mirror=False):
        """
        Draw the character on the screen.

        Args:
            x (float): The x-coordinate of the character's position.
            y (float): The y-coordinate of the character's position.
            mirror (bool): Whether to mirror the character horizontally.
        """
        if self.is_rainbow and self.current_anim not in {'soul_in', 'balloon_pop', 'balloon_popping'}:
            self.tex.draw_texture(self.name, self.current_anim + '_max', frame=self.anims[self.current_anim].attribute, x=x, y=y)
        else:
            if mirror:
                self.tex.draw_texture(self.name, self.current_anim, frame=self.anims[self.current_anim].attribute, x=x, y=y, mirror='horizontal')
            else:
                self.tex.draw_texture(self.name, self.current_anim, frame=self.anims[self.current_anim].attribute, x=x, y=y)
