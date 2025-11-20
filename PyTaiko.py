import logging
import os
from pathlib import Path
import sys

import sqlite3

import pyray as ray
from raylib.defines import (
    RL_FUNC_ADD,
    RL_ONE,
    RL_ONE_MINUS_SRC_ALPHA,
    RL_SRC_ALPHA,
)

from libs.audio import audio
from libs.global_data import PlayerNum
from libs.screen import Screen
from libs.tja import TJAParser
from libs.utils import (
    force_dedicated_gpu,
    global_data,
    global_tex
)
from libs.config import get_config
from scenes.devtest import DevScreen
from scenes.entry import EntryScreen
from scenes.game import GameScreen
from scenes.dan.game_dan import DanGameScreen
from scenes.practice.game import PracticeGameScreen
from scenes.practice.song_select import PracticeSongSelectScreen
from scenes.two_player.game import TwoPlayerGameScreen
from scenes.two_player.result import TwoPlayerResultScreen
from scenes.loading import LoadScreen
from scenes.result import ResultScreen
from scenes.settings import SettingsScreen
from scenes.song_select import SongSelectScreen
from scenes.title import TitleScreen
from scenes.two_player.song_select import TwoPlayerSongSelectScreen
from scenes.dan.dan_select import DanSelectScreen
from scenes.dan.dan_result import DanResultScreen


logger = logging.getLogger(__name__)

class Screens:
    TITLE = "TITLE"
    ENTRY = "ENTRY"
    SONG_SELECT = "SONG_SELECT"
    GAME = "GAME"
    GAME_2P = "GAME_2P"
    RESULT = "RESULT"
    RESULT_2P = "RESULT_2P"
    SONG_SELECT_2P = "SONG_SELECT_2P"
    DAN_SELECT = "DAN_SELECT"
    GAME_DAN = "GAME_DAN"
    DAN_RESULT = "DAN_RESULT"
    PRACTICE_SELECT = "PRACTICE_SELECT"
    GAME_PRACTICE = "GAME_PRACTICE"
    SETTINGS = "SETTINGS"
    DEV_MENU = "DEV_MENU"
    LOADING = "LOADING"

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record = logging.makeLogRecord(record.__dict__)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

def create_song_db():
    """Create the scores database if it doesn't exist
    The migration will eventually be removed"""
    with sqlite3.connect('scores.db') as con:
        cursor = con.cursor()
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS Scores (
            hash TEXT PRIMARY KEY,
            en_name TEXT NOT NULL,
            jp_name TEXT NOT NULL,
            diff INTEGER,
            score INTEGER,
            good INTEGER,
            ok INTEGER,
            bad INTEGER,
            drumroll INTEGER,
            combo INTEGER,
            clear INTEGER
        );
        '''
        cursor.execute(create_table_query)
        con.commit()
        logger.info("Scores database created successfully")

def main():
    force_dedicated_gpu()
    global_data.config = get_config()
    log_level = global_data.config["general"]["log_level"]
    colored_formatter = ColoredFormatter('[%(levelname)s] %(name)s: %(message)s')
    plain_formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(colored_formatter)

    file_handler = logging.FileHandler("latest.log")
    file_handler.setFormatter(plain_formatter)
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler]
    )
    logger.info("Starting PyTaiko")

    logger.debug(f"Loaded config: {global_data.config}")
    screen_width = global_tex.screen_width
    screen_height = global_tex.screen_height

    if global_data.config["video"]["vsync"]:
        ray.set_config_flags(ray.ConfigFlags.FLAG_VSYNC_HINT)
        logger.info("VSync enabled")
    if global_data.config["video"]["target_fps"] != -1:
        ray.set_target_fps(global_data.config["video"]["target_fps"])
        logger.info(f"Target FPS set to {global_data.config['video']['target_fps']}")
    ray.set_config_flags(ray.ConfigFlags.FLAG_MSAA_4X_HINT)
    ray.set_trace_log_level(ray.TraceLogLevel.LOG_WARNING)

    ray.init_window(screen_width, screen_height, "PyTaiko")
    logger.info(f"Window initialized: {screen_width}x{screen_height}")
    global_tex.load_screen_textures('global')
    logger.info("Global screen textures loaded")
    global_tex.load_zip('chara', 'chara_0')
    global_tex.load_zip('chara', 'chara_1')
    logger.info("Chara textures loaded")
    if global_data.config["video"]["borderless"]:
        ray.toggle_borderless_windowed()
        logger.info("Borderless window enabled")
    if global_data.config["video"]["fullscreen"]:
        ray.toggle_fullscreen()
        logger.info("Fullscreen enabled")

    current_screen = Screens.LOADING
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        current_screen = Screens.GAME
        path = Path(os.path.abspath(sys.argv[1]))
        tja = TJAParser(path)
        max_difficulty = max(tja.metadata.course_data.keys())
        global_data.session_data[PlayerNum.P1].selected_song = path
        global_data.session_data[PlayerNum.P1].selected_difficulty = max_difficulty
        global_data.modifiers[PlayerNum.P1].auto = True
    logger.info(f"Initial screen: {current_screen}")

    audio.set_log_level((log_level-1)//10)
    old_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)
    audio.init_audio_device()
    os.dup2(old_stderr, 2)
    os.close(old_stderr)
    logger.info("Audio device initialized")

    create_song_db()

    title_screen = TitleScreen('title')
    entry_screen = EntryScreen('entry')
    song_select_screen = SongSelectScreen('song_select')
    song_select_screen_2p = TwoPlayerSongSelectScreen('song_select')
    load_screen = LoadScreen('loading')
    game_screen = GameScreen('game')
    game_screen_2p = TwoPlayerGameScreen('game')
    game_screen_practice = PracticeGameScreen('game')
    practice_select_screen = PracticeSongSelectScreen('song_select')
    result_screen = ResultScreen('result')
    result_screen_2p = TwoPlayerResultScreen('result')
    settings_screen = SettingsScreen('settings')
    dev_screen = DevScreen('dev')
    dan_select_screen = DanSelectScreen('dan_select')
    game_screen_dan = DanGameScreen('game_dan')
    dan_result_screen = DanResultScreen('dan_result')

    screen_mapping: dict[str, Screen] = {
        Screens.ENTRY: entry_screen,
        Screens.TITLE: title_screen,
        Screens.SONG_SELECT: song_select_screen,
        Screens.SONG_SELECT_2P: song_select_screen_2p,
        Screens.PRACTICE_SELECT: practice_select_screen,
        Screens.GAME: game_screen,
        Screens.GAME_2P: game_screen_2p,
        Screens.GAME_PRACTICE: game_screen_practice,
        Screens.RESULT: result_screen,
        Screens.RESULT_2P: result_screen_2p,
        Screens.SETTINGS: settings_screen,
        Screens.DEV_MENU: dev_screen,
        Screens.DAN_SELECT: dan_select_screen,
        Screens.GAME_DAN: game_screen_dan,
        Screens.DAN_RESULT: dan_result_screen,
        Screens.LOADING: load_screen
    }
    target = ray.load_render_texture(screen_width, screen_height)
    ray.gen_texture_mipmaps(target.texture)
    ray.set_texture_filter(target.texture, ray.TextureFilter.TEXTURE_FILTER_TRILINEAR)
    ray.rl_set_blend_factors_separate(RL_SRC_ALPHA, RL_ONE_MINUS_SRC_ALPHA, RL_ONE, RL_ONE_MINUS_SRC_ALPHA, RL_FUNC_ADD, RL_FUNC_ADD)
    ray.set_exit_key(global_data.config["keys"]["exit_key"])

    ray.hide_cursor()
    logger.info("Cursor hidden")
    last_fps = 1

    while not ray.window_should_close():
        if ray.is_key_pressed(global_data.config["keys"]["fullscreen_key"]):
            ray.toggle_fullscreen()
            logger.info("Toggled fullscreen")
        elif ray.is_key_pressed(global_data.config["keys"]["borderless_key"]):
            ray.toggle_borderless_windowed()
            logger.info("Toggled borderless windowed mode")

        curr_screen_width = ray.get_screen_width()
        curr_screen_height = ray.get_screen_height()

        if curr_screen_width == 0 or curr_screen_height == 0:
            dest_rect = ray.Rectangle(0, 0, screen_width, screen_height)
        else:
            scale = min(curr_screen_width / screen_width, curr_screen_height / screen_height)
            dest_rect = ray.Rectangle((curr_screen_width - (screen_width * scale)) * 0.5,
                (curr_screen_height - (screen_height * scale)) * 0.5,
                screen_width * scale, screen_height * scale)

        ray.begin_texture_mode(target)
        ray.begin_blend_mode(ray.BlendMode.BLEND_CUSTOM_SEPARATE)

        screen = screen_mapping[current_screen]

        next_screen = screen.update()
        if screen.screen_init:
            ray.clear_background(ray.BLACK)
            screen._do_draw()

        if next_screen is not None:
            logger.info(f"Screen changed from {current_screen} to {next_screen}")
            current_screen = next_screen
            global_data.input_locked = 0

        if global_data.config["general"]["fps_counter"]:
            curr_fps = ray.get_fps()
            if curr_fps != 0 and curr_fps != last_fps:
                last_fps = curr_fps
            if last_fps < 30:
                ray.draw_text(f'{last_fps} FPS', 20, 20, 20, ray.RED)
            elif last_fps < 60:
                ray.draw_text(f'{last_fps} FPS', 20, 20, 20, ray.YELLOW)
            else:
                ray.draw_text(f'{last_fps} FPS', 20, 20, 20, ray.LIME)
        ray.end_blend_mode()
        ray.end_texture_mode()
        ray.begin_drawing()
        ray.clear_background(ray.BLACK)
        ray.draw_texture_pro(
             target.texture,
             ray.Rectangle(0, 0, target.texture.width, -target.texture.height),
             dest_rect,
             ray.Vector2(0,0),
             0,
             ray.WHITE
        )
        ray.end_drawing()
    ray.close_window()
    audio.close_audio_device()
    logger.info("Window closed and audio device shut down")

if __name__ == "__main__":
    main()
