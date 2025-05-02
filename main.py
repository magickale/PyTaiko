import pyray as ray

from libs.audio import audio
from libs.utils import get_config
from scenes.entry import EntryScreen
from scenes.game import GameScreen
from scenes.result import ResultScreen
from scenes.song_select import SongSelectScreen
from scenes.title import TitleScreen


class Screens:
    TITLE = "TITLE"
    ENTRY = "ENTRY"
    SONG_SELECT = "SONG_SELECT"
    GAME = "GAME"
    RESULT = "RESULT"

def main():
    screen_width: int = get_config()["video"]["screen_width"]
    screen_height: int = get_config()["video"]["screen_height"]
    render_width, render_height = ray.get_render_width(), ray.get_render_height()
    dpi_scale = ray.get_window_scale_dpi()
    if dpi_scale.x == 0:
        dpi_scale = (ray.get_render_width(), ray.get_render_height())
        dpi_scale = screen_width, screen_height
    else:
        dpi_scale = int(render_width/dpi_scale.x), int(render_height/dpi_scale.y)

    if get_config()["video"]["vsync"]:
        ray.set_config_flags(ray.ConfigFlags.FLAG_VSYNC_HINT)
    ray.set_config_flags(ray.ConfigFlags.FLAG_MSAA_4X_HINT)

    ray.set_window_max_size(screen_width, screen_height)
    ray.set_window_min_size(screen_width, screen_height)
    ray.init_window(screen_width, screen_height, "PyTaiko")
    if get_config()["video"]["borderless"]:
        ray.toggle_borderless_windowed()
    ray.clear_window_state(ray.ConfigFlags.FLAG_WINDOW_TOPMOST)
    if get_config()["video"]["fullscreen"]:
        ray.maximize_window()

    current_screen = Screens.TITLE
    _frames_counter = 0

    audio.init_audio_device()

    title_screen = TitleScreen(screen_width, screen_height)
    entry_screen = EntryScreen(screen_width, screen_height)
    song_select_screen = SongSelectScreen(screen_width, screen_height)
    game_screen = GameScreen(screen_width, screen_height)
    result_screen = ResultScreen(screen_width, screen_height)

    screen_mapping = {
        Screens.ENTRY: entry_screen,
        Screens.TITLE: title_screen,
        Screens.SONG_SELECT: song_select_screen,
        Screens.GAME: game_screen,
        Screens.RESULT: result_screen
    }
    target = ray.load_render_texture(screen_width, screen_height)
    ray.set_texture_filter(target.texture, ray.TextureFilter.TEXTURE_FILTER_TRILINEAR)
    #lmaooooooooooooo
    #rl_set_blend_factors_separate(RL_SRC_ALPHA, RL_ONE_MINUS_SRC_ALPHA, RL_ONE, RL_ONE_MINUS_SRC_ALPHA, RL_FUNC_ADD, RL_FUNC_ADD)
    ray.rl_set_blend_factors_separate(0x302, 0x303, 1, 0x303, 0x8006, 0x8006)
    ray.set_exit_key(ray.KeyboardKey.KEY_A)
    while not ray.window_should_close():

        ray.begin_texture_mode(target)
        ray.begin_blend_mode(ray.BlendMode.BLEND_CUSTOM_SEPARATE)
        screen = screen_mapping[current_screen]

        if ray.is_key_pressed(ray.KeyboardKey.KEY_F11):
            ray.toggle_fullscreen()

        next_screen = screen.update()
        screen.draw()
        if screen == title_screen:
            ray.clear_background(ray.BLACK)
        else:
            ray.clear_background(ray.WHITE)

        if next_screen is not None:
            current_screen = next_screen

        if get_config()["general"]["fps_counter"]:
            ray.draw_fps(20, 20)
        ray.end_blend_mode()
        ray.end_texture_mode()
        ray.begin_drawing()
        ray.clear_background(ray.WHITE)
        #Thanks to rnoiz proper render height
        ray.draw_texture_pro(
             target.texture,
             ray.Rectangle(0, 0, target.texture.width, -target.texture.height),
             ray.Rectangle(0, 0, dpi_scale[0], dpi_scale[1]),
             ray.Vector2(0,0),
             0,
             ray.WHITE
        )
        ray.end_drawing()
    ray.close_window()
    audio.close_audio_device()

if __name__ == "__main__":
    main()
