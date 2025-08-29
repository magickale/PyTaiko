import threading

import pyray as ray

from libs.animation import Animation
from libs.song_hash import build_song_hashes
from libs.texture import tex
from libs.utils import get_current_ms, global_data
from scenes.song_select import SongSelectScreen


class LoadScreen:
    def __init__(self, song_select_screen: SongSelectScreen):
        self.width = 1280
        self.height = 720
        self.screen_init = False
        self.songs_loaded = False
        self.navigator_started = False
        self.loading_complete = False
        self.song_select_screen = song_select_screen

        # Progress bar settings
        self.progress_bar_width = self.width * 0.43
        self.progress_bar_height = 50
        self.progress_bar_x = (self.width - self.progress_bar_width) // 2
        self.progress_bar_y = self.height * 0.85

        # Thread references
        self.loading_thread = None
        self.navigator_thread = None

        self.fade_in = None

    def _load_song_hashes(self):
        """Background thread function to load song hashes"""
        global_data.song_hashes = build_song_hashes()
        self.songs_loaded = True

    def _load_navigator(self):
        """Background thread function to load navigator"""
        self.song_select_screen.load_navigator()
        self.loading_complete = True

    def on_screen_start(self):
        if not self.screen_init:
            tex.load_screen_textures('loading')
            self.loading_thread = threading.Thread(target=self._load_song_hashes)
            self.loading_thread.daemon = True
            self.loading_thread.start()
            self.screen_init = True

    def on_screen_end(self, next_screen: str):
        self.screen_init = False
        tex.unload_textures()
        if self.loading_thread and self.loading_thread.is_alive():
            self.loading_thread.join(timeout=1.0)
        if self.navigator_thread and self.navigator_thread.is_alive():
            self.navigator_thread.join(timeout=1.0)

        return next_screen

    def update(self):
        self.on_screen_start()

        if self.songs_loaded and not self.navigator_started:
            self.navigator_thread = threading.Thread(target=self._load_navigator)
            self.navigator_thread.daemon = True
            self.navigator_thread.start()
            self.navigator_started = True

        if self.loading_complete and self.fade_in is None:
            self.fade_in = Animation.create_fade(1000, initial_opacity=0.0, final_opacity=1.0, ease_in='cubic')
            self.fade_in.start()

        if self.fade_in is not None:
            self.fade_in.update(get_current_ms())
            if self.fade_in.is_finished:
                return self.on_screen_end('TITLE')

    def draw(self):
        ray.draw_rectangle(0, 0, self.width, self.height, ray.BLACK)
        tex.draw_texture('kidou', 'warning')

        # Draw progress bar background
        ray.draw_rectangle(
            int(self.progress_bar_x),
            int(self.progress_bar_y),
            int(self.progress_bar_width),
            int(self.progress_bar_height),
            ray.Color(101, 0, 0, 255)
        )

        # Draw progress bar fill
        progress = max(0.0, min(1.0, global_data.song_progress))
        fill_width = self.progress_bar_width * progress
        if fill_width > 0:
            ray.draw_rectangle(
                int(self.progress_bar_x),
                int(self.progress_bar_y),
                int(fill_width),
                int(self.progress_bar_height),
                ray.RED
            )

        if self.fade_in is not None:
            ray.draw_rectangle(0, 0, self.width, self.height, ray.fade(ray.WHITE, self.fade_in.attribute))
    def draw_3d(self):
        pass
