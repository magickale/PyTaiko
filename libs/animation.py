from typing import Optional

from libs.utils import get_current_ms


class BaseAnimation():
    def __init__(self, duration: float, delay: float = 0.0) -> None:
        """
        Initialize a base animation.

        Args:
            duration: Length of the animation in milliseconds
            delay: Time to wait before starting the animation
            reverse_delay: If provided, animation will play in reverse after this delay
        """
        self.duration = duration
        self.delay = delay
        self.start_ms = get_current_ms()
        self.is_finished = False
        self.attribute = 0

    def update(self, current_time_ms: float) -> None:
        """Update the animation based on the current time."""
        pass

    def restart(self) -> None:
        self.start_ms = get_current_ms()
        self.is_finished = False

    def _ease_in(self, progress: float, ease_type: str) -> float:
        if ease_type == "quadratic":
            return progress * progress
        elif ease_type == "cubic":
            return progress * progress * progress
        elif ease_type == "exponential":
            return 0 if progress == 0 else pow(2, 10 * (progress - 1))
        return progress

    def _ease_out(self, progress: float, ease_type: str) -> float:
        if ease_type == "quadratic":
            return progress * (2 - progress)
        elif ease_type == "cubic":
            return 1 - pow(1 - progress, 3)
        elif ease_type == "exponential":
            return 1 if progress == 1 else 1 - pow(2, -10 * progress)
        return progress

    def _apply_easing(self, progress: float, ease_in: Optional[str] = None,
                         ease_out: Optional[str] = None) -> float:
        if ease_in:
            return self._ease_in(progress, ease_in)
        elif ease_out:
            return self._ease_out(progress, ease_out)
        return progress

class FadeAnimation(BaseAnimation):
    def __init__(self, duration: float, initial_opacity: float = 1.0,
                     final_opacity: float = 0.0, delay: float = 0.0,
                     ease_in: Optional[str] = None, ease_out: Optional[str] = None,
                     reverse_delay: Optional[float] = None) -> None:
        super().__init__(duration, delay)
        self.initial_opacity = initial_opacity
        self.final_opacity = final_opacity
        self.initial_opacity_saved = initial_opacity
        self.final_opacity_saved = final_opacity
        self.ease_in = ease_in
        self.ease_out = ease_out
        self.reverse_delay = reverse_delay
        self.reverse_delay_saved = reverse_delay

    def restart(self) -> None:
        super().restart()
        self.reverse_delay = self.reverse_delay_saved
        self.initial_opacity = self.initial_opacity_saved
        self.final_opacity = self.final_opacity_saved

    def update(self, current_time_ms: float) -> None:
        elapsed_time = current_time_ms - self.start_ms

        if elapsed_time <= self.delay:
            self.attribute = self.initial_opacity
        elif elapsed_time >= self.delay + self.duration:
            self.attribute = self.final_opacity

            if self.reverse_delay is not None:
                self.start_ms = current_time_ms
                self.delay = self.reverse_delay
                self.initial_opacity, self.final_opacity = self.final_opacity, self.initial_opacity
                self.reverse_delay = None
            else:
                self.is_finished = True
        else:
            animation_time = elapsed_time - self.delay
            progress = animation_time / self.duration
            progress = max(0.0, min(1.0, progress))
            progress = self._apply_easing(progress, self.ease_in, self.ease_out)
            self.attribute = self.initial_opacity + progress * (self.final_opacity - self.initial_opacity)

class MoveAnimation(BaseAnimation):
    def __init__(self, duration: float, total_distance: int = 0,
                      start_position: int = 0, delay: float = 0.0,
                      reverse_delay: Optional[float] = None,
                      ease_in: Optional[str] = None, ease_out: Optional[str] = None) -> None:
        super().__init__(duration, delay)
        self.reverse_delay = reverse_delay
        self.reverse_delay_saved = reverse_delay
        self.total_distance = total_distance
        self.start_position = start_position
        self.total_distance_saved = total_distance
        self.start_position_saved = start_position
        self.ease_in = ease_in
        self.ease_out = ease_out

    def restart(self) -> None:
        super().restart()
        self.reverse_delay = self.reverse_delay_saved
        self.total_distance = self.total_distance_saved
        self.start_position = self.start_position_saved

    def update(self, current_time_ms: float) -> None:
        elapsed_time = current_time_ms - self.start_ms
        if elapsed_time < self.delay:
            self.attribute = self.start_position

        elif elapsed_time >= self.delay + self.duration:
            self.attribute = self.start_position + self.total_distance
            if self.reverse_delay is not None:
                self.start_ms = current_time_ms
                self.delay = self.reverse_delay
                self.start_position = self.start_position + self.total_distance
                self.total_distance = -(self.total_distance)
                self.reverse_delay = None
            else:
                self.is_finished = True
        else:
            progress = (elapsed_time - self.delay) / self.duration
            progress = self._apply_easing(progress, self.ease_in, self.ease_out)
            self.attribute = self.start_position + (self.total_distance * progress)

class TextureChangeAnimation(BaseAnimation):
    def __init__(self, duration: float, textures: list[tuple[float, float, int]], delay: float = 0.0) -> None:
        super().__init__(duration)
        self.textures = textures
        self.delay = delay

    def update(self, current_time_ms: float) -> None:
        elapsed_time = current_time_ms - self.start_ms - self.delay
        if elapsed_time <= self.duration:
            for start, end, index in self.textures:
                if start < elapsed_time <= end:
                    self.attribute = index
        else:
            self.is_finished = True

class TextStretchAnimation(BaseAnimation):
    def __init__(self, duration: float) -> None:
        super().__init__(duration)
    def update(self, current_time_ms: float) -> None:
        elapsed_time = current_time_ms - self.start_ms
        if elapsed_time <= self.duration:
            self.attribute = 2 + 5 * (elapsed_time // 25)
        elif elapsed_time <= self.duration + 116:
            frame_time = (elapsed_time - self.duration) // 16.57
            self.attribute = 2 + 10 - (2 * (frame_time + 1))
        else:
            self.attribute = 0
            self.is_finished = True

class TextureResizeAnimation(BaseAnimation):
    def __init__(self, duration: float, initial_size: float = 1.0,
                     final_size: float = 0.0, delay: float = 0.0,
                     reverse_delay: Optional[float] = None,
                     ease_in: Optional[str] = None, ease_out: Optional[str] = None) -> None:
        super().__init__(duration, delay)
        self.initial_size = initial_size
        self.final_size = final_size
        self.reverse_delay = reverse_delay
        self.initial_size_saved = initial_size
        self.final_size_saved = final_size
        self.reverse_delay_saved = reverse_delay
        self.ease_in = ease_in
        self.ease_out = ease_out

    def restart(self) -> None:
        super().restart()
        self.reverse_delay = self.reverse_delay_saved
        self.initial_size = self.initial_size_saved
        self.final_size = self.final_size_saved


    def update(self, current_time_ms: float) -> None:
        elapsed_time = current_time_ms - self.start_ms

        if elapsed_time <= self.delay:
            self.attribute = self.initial_size
        elif elapsed_time >= self.delay + self.duration:
            self.attribute = self.final_size

            if self.reverse_delay is not None:
                self.start_ms = current_time_ms
                self.delay = self.reverse_delay
                self.initial_size, self.final_size = self.final_size, self.initial_size
                self.reverse_delay = None
            else:
                self.is_finished = True
        else:
            animation_time = elapsed_time - self.delay
            progress = animation_time / self.duration
            progress = self._apply_easing(progress, self.ease_in, self.ease_out)
            self.attribute = self.initial_size + ((self.final_size - self.initial_size) * progress)


class Animation:
    """Factory for creating different types of animations."""

    @staticmethod
    def create_fade(duration: float, **kwargs) -> FadeAnimation:
        """Create a fade animation.

        Args:
            duration: Length of the fade in milliseconds
            delay: Time to wait before starting the fade
            initial_opacity: Default is 1.0
            final_opacity: Default is 0.0
            reverse_delay: If provided, fade will play in reverse after this delay
            ease_in: Control ease into the fade
            ease_out: Control ease out of the fade

        Easing options:
            quadratic,
            cubic,
            exponential
        """
        return FadeAnimation(duration, **kwargs)

    @staticmethod
    def create_move(duration: float, **kwargs) -> MoveAnimation:
        """Create a movement animation.

        Args:
            duration: Length of the move in milliseconds
            start_position: The coordinates of the object before the move
            total_distance: The distance travelled from the start to end position
            reverse_delay: If provided, move will play in reverse after this delay
            delay: Time to wait before starting the move
            ease_in: Control ease into the move
            ease_out: Control ease out of the move

        Easing options:
            quadratic,
            cubic,
            exponential
        """
        return MoveAnimation(duration, **kwargs)


    @staticmethod
    def create_texture_change(duration: float, **kwargs) -> TextureChangeAnimation:
        """Create a texture change animation

        Args:
            duration: Length of the change in milliseconds
            textures: Passed in as a tuple of the starting millisecond, ending millisecond, and texture index
            delay: Time to wait before starting the change
        """
        return TextureChangeAnimation(duration, **kwargs)

    @staticmethod
    def create_text_stretch(duration: float) -> TextStretchAnimation:
        """Create a text stretch animation.

        Args:
            duration: Length of the stretch in milliseconds
        """
        return TextStretchAnimation(duration)

    @staticmethod
    def create_texture_resize(duration: float, **kwargs) -> TextureResizeAnimation:
        """Create a texture resize animation.

        Args:
            duration: Length of the change in milliseconds
            initial_size: Default is 1.0
            final_size: Default is 0.0
            delay: Time to wait before starting the resize
            reverse_delay: If provided, resize will play in reverse after this delay
        """
        return TextureResizeAnimation(duration, **kwargs)
