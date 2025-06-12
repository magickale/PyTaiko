import sqlite3
from pathlib import Path

import pyray as ray
from raylib.defines import (
    RL_FUNC_ADD,
    RL_ONE,
    RL_ONE_MINUS_SRC_ALPHA,
    RL_SRC_ALPHA,
)

from libs import song_hash
from libs.audio import audio
from libs.utils import get_config, global_data, load_all_textures_from_zip
from scenes.entry import EntryScreen
from scenes.game import GameScreen
from scenes.result import ResultScreen
from scenes.settings import SettingsScreen
from scenes.song_select import SongSelectScreen
from scenes.title import TitleScreen


class Screens:
    TITLE = "TITLE"
    ENTRY = "ENTRY"
    SONG_SELECT = "SONG_SELECT"
    GAME = "GAME"
    RESULT = "RESULT"
    SETTINGS = "SETTINGS"

def create_song_db():
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
    print("Scores database created successfully")

def main():
    create_song_db()
    song_hash.song_hashes = song_hash.build_song_hashes()
    global_data.config = get_config()
    screen_width: int = global_data.config["video"]["screen_width"]
    screen_height: int = global_data.config["video"]["screen_height"]
    render_width, render_height = ray.get_render_width(), ray.get_render_height()
    dpi_scale = ray.get_window_scale_dpi()
    if dpi_scale.x == 0:
        dpi_scale = (ray.get_render_width(), ray.get_render_height())
        dpi_scale = screen_width, screen_height
    else:
        dpi_scale = int(render_width/dpi_scale.x), int(render_height/dpi_scale.y)

    if global_data.config["video"]["vsync"]:
        ray.set_config_flags(ray.ConfigFlags.FLAG_VSYNC_HINT)
    ray.set_config_flags(ray.ConfigFlags.FLAG_MSAA_4X_HINT)
    ray.set_trace_log_level(ray.TraceLogLevel.LOG_ERROR)

    #ray.set_window_max_size(screen_width, screen_height)
    #ray.set_window_min_size(screen_width, screen_height)
    ray.init_window(screen_width, screen_height, "PyTaiko")
    if global_data.config["video"]["borderless"]:
        ray.toggle_borderless_windowed()
    #ray.clear_window_state(ray.ConfigFlags.FLAG_WINDOW_TOPMOST)
    if global_data.config["video"]["fullscreen"]:
        ray.maximize_window()

    current_screen = Screens.TITLE
    _frames_counter = 0

    audio.init_audio_device()

    title_screen = TitleScreen(screen_width, screen_height)
    entry_screen = EntryScreen(screen_width, screen_height)
    song_select_screen = SongSelectScreen(screen_width, screen_height)
    game_screen = GameScreen(screen_width, screen_height)
    result_screen = ResultScreen(screen_width, screen_height)
    settings_screen = SettingsScreen(screen_width, screen_height)

    screen_mapping = {
        Screens.ENTRY: entry_screen,
        Screens.TITLE: title_screen,
        Screens.SONG_SELECT: song_select_screen,
        Screens.GAME: game_screen,
        Screens.RESULT: result_screen,
        Screens.SETTINGS: settings_screen
    }
    target = ray.load_render_texture(screen_width, screen_height)
    ray.set_texture_filter(target.texture, ray.TextureFilter.TEXTURE_FILTER_TRILINEAR)
    ray.gen_texture_mipmaps(target.texture)
    ray.rl_set_blend_factors_separate(RL_SRC_ALPHA, RL_ONE_MINUS_SRC_ALPHA, RL_ONE, RL_ONE_MINUS_SRC_ALPHA, RL_FUNC_ADD, RL_FUNC_ADD)
    ray.set_exit_key(ray.KeyboardKey.KEY_A)
    global_data.textures = load_all_textures_from_zip(Path('Graphics/lumendata/intermission.zip'))
    while not ray.window_should_close():

        ray.begin_texture_mode(target)
        ray.begin_blend_mode(ray.BlendMode.BLEND_CUSTOM_SEPARATE)
        screen = screen_mapping[current_screen]

        if ray.is_key_pressed(ray.KeyboardKey.KEY_F11):
            ray.toggle_fullscreen()

        next_screen = screen.update()
        ray.clear_background(ray.BLACK)
        screen.draw()

        if next_screen is not None:
            current_screen = next_screen

        if global_data.config["general"]["fps_counter"]:
            ray.draw_fps(20, 20)
        ray.end_blend_mode()
        ray.end_texture_mode()
        ray.begin_drawing()
        ray.clear_background(ray.WHITE)
        #Thanks to rnoiz proper render height
        ray.draw_texture_pro(
             target.texture,
             ray.Rectangle(0, 0, target.texture.width, -target.texture.height),
             ray.Rectangle(0, 0, screen_width, screen_height),
             ray.Vector2(0,0),
             0,
             ray.WHITE
        )
        ray.end_drawing()
    ray.close_window()
    audio.close_audio_device()

if __name__ == "__main__":
    main()
