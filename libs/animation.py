class Animation:
    def __init__(self, current_ms: float, duration: float, type: str):
        self.type = type
        self.start_ms = current_ms
        self.attribute = 0
        self.duration = duration
        self.params = dict()
        self.is_finished = False

    def update(self, current_ms: float):
        if self.type == 'fade':
            self.fade(current_ms,
                self.duration,
                initial_opacity=self.params.get('initial_opacity', 1.0),
                final_opacity=self.params.get('final_opacity', 0.0),
                delay=self.params.get('delay', 0.0),
                ease_in=self.params.get('ease_in', None),
                ease_out=self.params.get('ease_out', None))
            if self.params.get('reverse', None) is not None and current_ms - self.start_ms >= self.duration + self.params.get('delay', 0.0):
                self.fade(current_ms,
                    self.duration,
                    final_opacity=self.params.get('initial_opacity', 1.0),
                    initial_opacity=self.params.get('final_opacity', 0.0),
                    delay=self.params.get('delay', 0.0) + self.duration + self.params.get('reverse'),
                    ease_in=self.params.get('ease_in', None),
                    ease_out=self.params.get('ease_out', None))
        elif self.type == 'move':
            self.move(current_ms,
                self.duration,
                self.params['total_distance'],
                self.params['start_position'],
                delay=self.params.get('delay', 0.0),
                ease_in=self.params.get('ease_in', None),
                ease_out=self.params.get('ease_out', None))
        elif self.type == 'texture_change':
            self.texture_change(current_ms,
                self.duration,
                self.params['textures'])
        elif self.type == 'text_stretch':
            self.text_stretch(current_ms,
                self.duration)
        elif self.type == 'texture_resize':
            self.texture_resize(current_ms,
                self.duration,
                initial_size=self.params.get('initial_size', 1.0),
                final_size=self.params.get('final_size', 1.0),
                delay=self.params.get('delay', 0.0))
            if self.params.get('reverse', None) is not None and current_ms - self.start_ms >= self.duration + self.params.get('delay', 0.0):
                self.texture_resize(current_ms,
                    self.duration,
                    final_size=self.params.get('initial_size', 1.0),
                    initial_size=self.params.get('final_size', 1.0),
                    delay=self.params.get('delay', 0.0) + self.duration)

    def _ease_out_progress(self, progress: float, ease: str | None) -> float:
        if ease == 'quadratic':
            return progress * (2 - progress)
        elif ease == 'cubic':
            return 1 - pow(1 - progress, 3)
        elif ease == 'exponential':
            return 1 - pow(2, -10 * progress)
        else:
            return progress
    def _ease_in_progress(self, progress: float, ease: str | None) -> float:
        if ease == 'quadratic':
            return progress * progress
        elif ease == 'cubic':
            return progress * progress * progress
        elif ease == 'exponential':
            return pow(2, 10 * (progress - 1))
        else:
            return progress

    def fade(self, current_ms: float, duration: float, initial_opacity: float, final_opacity: float, delay: float, ease_in: str | None, ease_out: str | None) -> None:
        elapsed_time = current_ms - self.start_ms
        if elapsed_time < delay:
            self.attribute = initial_opacity

        elapsed_time -= delay
        if elapsed_time >= duration:
            self.attribute = final_opacity
            self.is_finished = True

        if ease_in is not None:
            progress = self._ease_in_progress(elapsed_time / duration, ease_in)
        elif ease_out is not None:
            progress = self._ease_out_progress(elapsed_time / duration, ease_out)
        else:
            progress = elapsed_time / duration

        current_opacity = initial_opacity + (final_opacity - initial_opacity) * progress
        self.attribute = current_opacity
    def move(self, current_ms: float, duration: float, total_distance: float, start_position: float, delay: float, ease_in: str | None, ease_out: str | None) -> None:
        elapsed_time = current_ms - self.start_ms
        if elapsed_time < delay:
            self.attribute = start_position

        elapsed_time -= delay
        if elapsed_time <= duration:
            if ease_in is not None:
                progress = self._ease_in_progress(elapsed_time / duration, ease_in)
            elif ease_out is not None:
                progress = self._ease_out_progress(elapsed_time / duration, ease_out)
            else:
                progress = elapsed_time / duration
            self.attribute = start_position + (total_distance * progress)
        else:
            self.attribute = start_position + total_distance
            self.is_finished = True
    def texture_change(self, current_ms: float, duration: float, textures: list[tuple[float, float, int]]) -> None:
        elapsed_time = current_ms - self.start_ms
        if elapsed_time <= duration:
            for start, end, index in textures:
                if start < elapsed_time <= end:
                    self.attribute = index
        else:
            self.is_finished = True
    def text_stretch(self, current_ms: float, duration: float):
        elapsed_time = current_ms - self.start_ms
        if elapsed_time <= duration:
            self.attribute = 2 + 5 * (elapsed_time // 25)
        elif elapsed_time <= duration + 116:
            frame_time = (elapsed_time - duration) // 16.57
            self.attribute = 2 + 10 - (2 * (frame_time + 1))
        else:
            self.attribute = 0
            self.is_finished = True
    def texture_resize(self, current_ms: float, duration: float, initial_size: float, final_size: float, delay: float):
        elapsed_time = current_ms - self.start_ms
        if elapsed_time < delay:
            self.attribute = initial_size
        elapsed_time -= delay
        if elapsed_time >= duration:
            self.attribute = final_size
            self.is_finished = True
        elif elapsed_time < duration:
            progress = elapsed_time / duration
            self.attribute = initial_size + ((final_size - initial_size) * progress)
        else:
            self.attribute = final_size
            self.is_finished = True
