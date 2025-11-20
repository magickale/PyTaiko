import logging
import threading

import pyray as ray

from libs.animation import Animation
from libs.global_objects import AllNetIcon
from libs.screen import Screen
from libs.song_hash import build_song_hashes
from libs.texture import tex
from libs.utils import get_current_ms, global_data
from libs.file_navigator import navigator


logger = logging.getLogger(__name__)

class LoadScreen(Screen):
    def __init__(self, name: str):
        super().__init__(name)
        self.width = tex.screen_width
        self.height = tex.screen_height
        self.songs_loaded = False
        self.navigator_started = False
        self.loading_complete = False
        self.navigator = navigator

        # Progress bar settings
        self.progress_bar_width = self.width * 0.43
        self.progress_bar_height = 50
        self.progress_bar_x = (self.width - self.progress_bar_width) // 2
        self.progress_bar_y = self.height * 0.85

        # Thread references
        self.loading_thread = None
        self.navigator_thread = None

        self.fade_in = None
        self.allnet_indicator = AllNetIcon()

    def _load_song_hashes(self):
        """Background thread function to load song hashes"""
        global_data.song_hashes = build_song_hashes()
        self.songs_loaded = True
        logger.info("Song hashes loaded")

    def _load_navigator(self):
        """Background thread function to load navigator"""
        self.navigator.initialize(global_data.config["paths"]["tja_path"])
        self.loading_complete = True
        logger.info("Navigator initialized")

    def on_screen_start(self):
        tex.load_screen_textures(self.screen_name)
        logger.info(f"Loaded textures for screen: {self.screen_name}")
        self.loading_thread = threading.Thread(target=self._load_song_hashes)
        self.loading_thread.daemon = True
        self.loading_thread.start()
        logger.info("Started song hashes loading thread")

    def on_screen_end(self, next_screen: str):
        if self.loading_thread and self.loading_thread.is_alive():
            self.loading_thread.join(timeout=1.0)
            logger.info("Joined song hashes loading thread")
        if self.navigator_thread and self.navigator_thread.is_alive():
            self.navigator_thread.join(timeout=1.0)
            logger.info("Joined navigator loading thread")
        return super().on_screen_end(next_screen)

    def update(self):
        super().update()

        if self.songs_loaded and not self.navigator_started:
            self.navigator_thread = threading.Thread(target=self._load_navigator)
            self.navigator_thread.daemon = True
            self.navigator_thread.start()
            self.navigator_started = True
            logger.info("Started navigator loading thread")

        if self.loading_complete and self.fade_in is None:
            self.fade_in = Animation.create_fade(1000, initial_opacity=0.0, final_opacity=1.0, ease_in='cubic')
            self.fade_in.start()
            logger.info("Fade-in animation started")

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
        self.allnet_indicator.draw()
