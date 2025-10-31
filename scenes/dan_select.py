
import logging
import pyray as ray

from libs.audio import audio
from libs.global_data import global_data
from libs.texture import tex
from libs.chara_2d import Chara2D
from libs.global_objects import AllNetIcon, CoinOverlay, Indicator, Nameplate, Timer
from libs.screen import Screen
from libs.file_navigator import DanCourse, navigator
from libs.transition import Transition
from libs.utils import get_current_ms, is_l_don_pressed, is_l_kat_pressed, is_r_don_pressed, is_r_kat_pressed
from scenes.song_select import SongSelectScreen, State

logger = logging.getLogger(__name__)

class DanSelectScreen(Screen):
    def on_screen_start(self):
        super().on_screen_start()
        self.navigator = navigator
        self.navigator.in_dan_select = True
        self.navigator.select_current_item()
        self.coin_overlay = CoinOverlay()
        self.allnet_indicator = AllNetIcon()
        self.timer = Timer(60, get_current_ms(), self.navigator.select_current_item)
        self.indicator = Indicator(Indicator.State.SELECT)
        self.player = DanSelectPlayer(str(global_data.player_num))
        self.state = State.BROWSING
        self.transition = Transition('', '')
        self.last_moved = 0
        audio.play_sound('bgm', 'music')
        audio.play_sound('dan_select', 'voice')

    def on_screen_end(self, next_screen: str):
        session_data = global_data.session_data[global_data.player_num-1]
        current_item = self.navigator.get_current_item()
        if isinstance(current_item, DanCourse):
            session_data.selected_song = current_item.charts[0]
            session_data.selected_dan = current_item.charts
            session_data.selected_dan_exam = current_item.exams
            session_data.song_title = current_item.title
            session_data.dan_color = current_item.color
        else:
            self.navigator.in_dan_select = False
            self.navigator.go_back()
        return super().on_screen_end(next_screen)

    def handle_input_browsing(self):
        """Handle input for browsing songs."""
        action = self.player.handle_input_browsing(self.last_moved, self.navigator.items[self.navigator.selected_index] if self.navigator.items else None)
        current_time = get_current_ms()
        if action == "skip_left":
            for _ in range(10):
                self.navigator.navigate_left()
            self.last_moved = current_time
        elif action == "skip_right":
            for _ in range(10):
                self.navigator.navigate_right()
            self.last_moved = current_time
        elif action == "navigate_left":
            self.navigator.navigate_left()
            self.last_moved = current_time
        elif action == "navigate_right":
            self.navigator.navigate_right()
            self.last_moved = current_time
        elif action == "go_back":
            return action
        elif action == "select_song":
            self.state = State.SONG_SELECTED

    def handle_input(self, state, screen):
        """Main input dispatcher. Delegates to state-specific handlers."""
        if state == State.BROWSING:
            return screen.handle_input_browsing()
        elif state == State.SONG_SELECTED:
            res = self.player.handle_input_selected()
            if res == 'confirm':
                self.transition.start()
            elif res == 'cancel':
                self.state = State.BROWSING

    def update(self):
        super().update()
        current_time = get_current_ms()
        self.indicator.update(current_time)
        self.timer.update(current_time)
        self.transition.update(current_time)
        if self.transition.is_finished:
            return self.on_screen_end("GAME_DAN")
        for song in self.navigator.items:
            song.box.update(False)
            song.box.is_open = song.box.position == SongSelectScreen.BOX_CENTER + 150
        self.player.update(current_time)
        res = self.handle_input(self.state, self)
        if res == 'go_back':
            return self.on_screen_end("SONG_SELECT")

    def draw(self):
        tex.draw_texture('global', 'bg')
        tex.draw_texture('global', 'bg_header')
        tex.draw_texture('global', 'bg_footer')
        tex.draw_texture('global', 'footer')
        for item in self.navigator.items:
            box = item.box
            if -156 <= box.position <= 1280 + 144:
                if box.position <= 500:
                    box.draw(box.position, 95, False)
                else:
                    box.draw(box.position, 95, False)
        if self.state == State.SONG_SELECTED:
            ray.draw_rectangle(0, 0, 1280, 720, ray.fade(ray.BLACK, min(0.5, self.player.confirmation_window.fade_in.attribute)))
        self.player.draw()
        self.indicator.draw(410, 575)
        self.timer.draw()
        self.coin_overlay.draw()
        tex.draw_texture('global', 'dan_select')
        self.transition.draw()
        self.allnet_indicator.draw()

class DanSelectPlayer:
    def __init__(self, player_num: str):
        self.player_num = player_num
        self.selected_difficulty = -3
        self.prev_diff = -3
        self.selected_song = False
        self.is_ura = False
        self.is_confirmed = False
        self.ura_toggle = 0
        self.diff_select_move_right = False
        self.neiro_selector = None
        self.modifier_selector = None
        self.confirmation_window = ConfirmationWindow()

        # Player-specific objects
        self.chara = Chara2D(int(self.player_num) - 1, 100)
        plate_info = global_data.config[f'nameplate_{self.player_num}p']
        self.nameplate = Nameplate(plate_info['name'], plate_info['title'],
            int(self.player_num), plate_info['dan'], plate_info['gold'], plate_info['title_bg'])

    def update(self, current_time):
        """Update player state"""
        self.nameplate.update(current_time)
        self.chara.update(current_time, 100, False, False)
        self.confirmation_window.update(current_time, self.is_confirmed)

    def handle_input_browsing(self, last_moved, selected_item):
        """Handle input for browsing songs. Returns action string or None."""
        current_time = get_current_ms()

        # Skip left (fast navigate)
        if ray.is_key_pressed(ray.KeyboardKey.KEY_LEFT_CONTROL) or (is_l_kat_pressed(self.player_num) and current_time <= last_moved + 50):
            audio.play_sound('skip', 'sound')
            return "skip_left"

        # Skip right (fast navigate)
        if ray.is_key_pressed(ray.KeyboardKey.KEY_RIGHT_CONTROL) or (is_r_kat_pressed(self.player_num) and current_time <= last_moved + 50):
            audio.play_sound('skip', 'sound')
            return "skip_right"

        # Navigate left
        if is_l_kat_pressed(self.player_num):
            audio.play_sound('kat', 'sound')
            return "navigate_left"

        # Navigate right
        if is_r_kat_pressed(self.player_num):
            audio.play_sound('kat', 'sound')
            return "navigate_right"

        # Select/Enter
        if is_l_don_pressed(self.player_num) or is_r_don_pressed(self.player_num):
            if selected_item is not None and selected_item.box.is_back:
                audio.play_sound('cancel', 'sound')
                return "go_back"
            else:
                self.confirmation_window.start()
                audio.play_sound('don', 'sound')
                audio.play_sound('confirm_box', 'sound')
                audio.play_sound('dan_confirm', 'voice')
                return "select_song"

        return None

    def handle_input(self, state, screen):
        """Main input dispatcher. Delegates to state-specific handlers."""
        if self.is_voice_playing():
            return

        if state == State.BROWSING:
            screen.handle_input_browsing()
        elif state == State.SONG_SELECTED:
            res = screen.handle_input_selected()

        if res:
            return res

    def handle_input_selected(self):
        """Handle input for selecting difficulty. Returns 'cancel', 'confirm', or None"""
        if is_l_kat_pressed(self.player_num):
            audio.play_sound('kat', 'sound')
            self.is_confirmed = False
        if is_r_kat_pressed(self.player_num):
            audio.play_sound('kat', 'sound')
            self.is_confirmed = True

        if is_l_don_pressed(self.player_num) or is_r_don_pressed(self.player_num):
            if self.is_confirmed:
                audio.play_sound('don', 'sound')
                return "confirm"
            else:
                self.confirmation_window = ConfirmationWindow()
                return "cancel"
        return None

    def draw(self):
        if self.player_num == '1':
            self.nameplate.draw(30, 640)
            self.chara.draw(x=-50, y=410)
        else:
            self.nameplate.draw(950, 640)
            self.chara.draw(mirror=True, x=950, y=410)

        self.confirmation_window.draw()

class ConfirmationWindow:
    def __init__(self):
        self.fade_in = tex.get_animation(8, is_copy=True)
        self.side = 0

    def start(self):
        self.fade_in.start()

    def update(self, current_time_ms: float, is_confirmed: bool):
        self.fade_in.update(current_time_ms)
        self.side = is_confirmed

    def draw(self):
        tex.draw_texture('confirm_box', 'bg', fade=self.fade_in.attribute)
        tex.draw_texture('confirm_box', 'confirmation_text', fade=self.fade_in.attribute)
        for i in range(2):
            tex.draw_texture('confirm_box', 'selection_box', index=i, fade=self.fade_in.attribute)

        tex.draw_texture('confirm_box', 'selection_box_highlight', index=self.side, fade=self.fade_in.attribute)
        tex.draw_texture('confirm_box', 'selection_box_outline', index=self.side, fade=self.fade_in.attribute)
        tex.draw_texture('confirm_box', 'yes', fade=self.fade_in.attribute)
        tex.draw_texture('confirm_box', 'no', fade=self.fade_in.attribute)
