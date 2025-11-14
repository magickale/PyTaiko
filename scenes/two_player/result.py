import logging
from libs.global_data import PlayerNum
from libs.utils import get_current_ms
from scenes.result import Background, FadeIn, ResultPlayer, ResultScreen

logger = logging.getLogger(__name__)

class TwoPlayerResultScreen(ResultScreen):
    def on_screen_start(self):
        super().on_screen_start()
        self.background = Background(PlayerNum.TWO_PLAYER, 1280)
        self.fade_in = FadeIn(PlayerNum.TWO_PLAYER)
        self.player_1 = ResultPlayer(PlayerNum.P1, True, False)
        self.player_2 = ResultPlayer(PlayerNum.P2, True, True)

    def update(self):
        super(ResultScreen, self).update()
        current_time = get_current_ms()
        self.fade_in.update(current_time)
        self.player_1.update(current_time, self.fade_in.is_finished, self.is_skipped)
        self.player_2.update(current_time, self.fade_in.is_finished, self.is_skipped)

        if current_time >= self.start_ms + 5000 and not self.fade_out.is_started:
            self.handle_input()

        self.fade_out.update(current_time)
        if self.fade_out.is_finished:
            self.fade_out.update(current_time)
            return self.on_screen_end("SONG_SELECT_2P")

    def draw(self):
        self.background.draw()
        self.draw_song_info()
        self.player_1.draw()
        self.player_2.draw()
        self.draw_overlay()
