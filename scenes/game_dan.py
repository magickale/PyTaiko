import logging
from libs.audio import audio
from libs.background import Background
from libs.global_data import global_data
from libs.transition import Transition
from scenes.game import GameScreen, SongInfo

logger = logging.getLogger(__name__)

class DanGameScreen(GameScreen):
    JUDGE_X = 414
    def on_screen_start(self):
        super().on_screen_start()
        self.init_tja(global_data.selected_song)
        logger.info(f"TJA initialized for song: {global_data.selected_song}")
        self.song_info = SongInfo(session_data.song_title, session_data.genre_index)
        self.background = Background(global_data.player_num, self.bpm, scene_preset='DAN')
        self.transition = Transition('', '', is_second=True)
        self.transition.start()

    def update(self):
        super().update()
        current_time = get_current_ms()
        self.transition.update(current_time)
        self.current_ms = current_time - self.start_ms
        self.start_song(current_time)
        self.update_background(current_time)

        if self.song_music is not None:
            audio.update_music_stream(self.song_music)

        self.player_1.update(self.current_ms, current_time, self.background)
        self.song_info.update(current_time)
        return self.global_keys()
