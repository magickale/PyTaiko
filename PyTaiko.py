import sqlite3

import pyray as ray
from raylib import CAMERA_ORTHOGRAPHIC
from raylib.defines import (
    RL_FUNC_ADD,
    RL_ONE,
    RL_ONE_MINUS_SRC_ALPHA,
    RL_SRC_ALPHA,
)

from libs.audio import audio
from libs.utils import (
    force_dedicated_gpu,
    get_config,
    global_data,
    global_tex
)
from scenes.devtest import DevScreen
from scenes.entry import EntryScreen
from scenes.game import GameScreen
from scenes.two_player.game import TwoPlayerGameScreen
from scenes.two_player.result import TwoPlayerResultScreen
from scenes.loading import LoadScreen
from scenes.result import ResultScreen
from scenes.settings import SettingsScreen
from scenes.song_select import SongSelectScreen
from scenes.title import TitleScreen
from scenes.two_player.song_select import TwoPlayerSongSelectScreen


class Screens:
    TITLE = "TITLE"
    ENTRY = "ENTRY"
    SONG_SELECT = "SONG_SELECT"
    GAME = "GAME"
    GAME_2P = "GAME_2P"
    RESULT = "RESULT"
    RESULT_2P = "RESULT_2P"
    SONG_SELECT_2P = "SONG_SELECT_2P"
    SETTINGS = "SETTINGS"
    DEV_MENU = "DEV_MENU"
    LOADING = "LOADING"

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
        # Migrate existing records: set clear=2 for full combos (bad=0)
        cursor.execute("""
            UPDATE Scores
            SET clear = 2
            WHERE bad = 0 AND (clear IS NULL OR clear <> 2)
        """)
        con.commit()
        print("Scores database created successfully")

def main():
    force_dedicated_gpu()
    global_data.config = get_config()
    screen_width: int = global_data.config["video"]["screen_width"]
    screen_height: int = global_data.config["video"]["screen_height"]

    if global_data.config["video"]["vsync"]:
        ray.set_config_flags(ray.ConfigFlags.FLAG_VSYNC_HINT)
    if global_data.config["video"]["target_fps"] != -1:
        ray.set_target_fps(global_data.config["video"]["target_fps"])
    ray.set_config_flags(ray.ConfigFlags.FLAG_MSAA_4X_HINT)
    ray.set_trace_log_level(ray.TraceLogLevel.LOG_WARNING)

    camera = ray.Camera3D()
    camera.position = ray.Vector3(0.0, 0.0, 10.0)  # Camera position
    camera.target = ray.Vector3(0.0, 0.0, 0.0)     # Camera looking at point
    camera.up = ray.Vector3(0.0, 1.0, 0.0)         # Camera up vector
    camera.fovy = screen_height  # For orthographic, this acts as the view height
    camera.projection = CAMERA_ORTHOGRAPHIC

    ray.init_window(screen_width, screen_height, "PyTaiko")
    global_tex.load_screen_textures('global')
    global_tex.load_zip('chara', 'chara_0')
    global_tex.load_zip('chara', 'chara_1')
    if global_data.config["video"]["borderless"]:
        ray.toggle_borderless_windowed()
    if global_data.config["video"]["fullscreen"]:
        ray.toggle_fullscreen()

    current_screen = Screens.LOADING

    audio.init_audio_device()

    create_song_db()

    title_screen = TitleScreen()
    entry_screen = EntryScreen()
    song_select_screen = SongSelectScreen()
    song_select_screen_2p = TwoPlayerSongSelectScreen()
    load_screen = LoadScreen()
    game_screen = GameScreen()
    game_screen_2p = TwoPlayerGameScreen()
    result_screen = ResultScreen()
    result_screen_2p = TwoPlayerResultScreen()
    settings_screen = SettingsScreen()
    dev_screen = DevScreen()

    screen_mapping = {
        Screens.ENTRY: entry_screen,
        Screens.TITLE: title_screen,
        Screens.SONG_SELECT: song_select_screen,
        Screens.SONG_SELECT_2P: song_select_screen_2p,
        Screens.GAME: game_screen,
        Screens.GAME_2P: game_screen_2p,
        Screens.RESULT: result_screen,
        Screens.RESULT_2P: result_screen_2p,
        Screens.SETTINGS: settings_screen,
        Screens.DEV_MENU: dev_screen,
        Screens.LOADING: load_screen
    }
    target = ray.load_render_texture(screen_width, screen_height)
    ray.set_texture_filter(target.texture, ray.TextureFilter.TEXTURE_FILTER_TRILINEAR)
    ray.gen_texture_mipmaps(target.texture)
    ray.rl_set_blend_factors_separate(RL_SRC_ALPHA, RL_ONE_MINUS_SRC_ALPHA, RL_ONE, RL_ONE_MINUS_SRC_ALPHA, RL_FUNC_ADD, RL_FUNC_ADD)
    ray.set_exit_key(ord(global_data.config["keys_1p"]["exit_key"]))

    ray.hide_cursor()

    while not ray.window_should_close():
        if ray.is_key_pressed(ray.KeyboardKey.KEY_F11):
            ray.toggle_fullscreen()
        elif ray.is_key_pressed(ray.KeyboardKey.KEY_F10):
            ray.toggle_borderless_windowed()

        ray.begin_texture_mode(target)
        ray.begin_blend_mode(ray.BlendMode.BLEND_CUSTOM_SEPARATE)

        screen = screen_mapping[current_screen]

        next_screen = screen.update()
        ray.clear_background(ray.BLACK)
        screen.draw()
        #ray.begin_mode_3d(camera)
        #screen.draw_3d()
       # ray.end_mode_3d()

        if next_screen is not None:
            current_screen = next_screen
            global_data.input_locked = 0

        if global_data.config["general"]["fps_counter"]:
            ray.draw_fps(20, 20)
        ray.end_blend_mode()
        ray.end_texture_mode()
        ray.begin_drawing()
        ray.clear_background(ray.WHITE)
        ray.draw_texture_pro(
             target.texture,
             ray.Rectangle(0, 0, target.texture.width, -target.texture.height),
             ray.Rectangle(0, 0, ray.get_screen_width(), ray.get_screen_height()),
             ray.Vector2(0,0),
             0,
             ray.WHITE
        )
        ray.end_drawing()
    ray.close_window()
    audio.close_audio_device()

if __name__ == "__main__":
    main()
