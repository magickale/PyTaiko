import copy
from pathlib import Path
from libs.tja import TJAParser
from libs.utils import get_current_ms
from libs.audio import audio
from libs.utils import global_data, session_data
from libs.video import VideoPlayer
from scenes.game import ClearAnimation, FCAnimation, FailAnimation, GameScreen, Player, Background, SCREEN_WIDTH

class TwoPlayerGameScreen(GameScreen):
    def on_screen_start(self):
        if not self.screen_init:
            super().on_screen_start()
            scene_preset = self.tja.metadata.scene_preset
            if self.background is not None:
                self.background.unload()
            self.background = Background(3, self.bpm, scene_preset=scene_preset)

    def load_hitsounds(self):
        """Load the hit sounds"""
        sounds_dir = Path("Sounds")
        if global_data.hit_sound == -1:
            audio.load_sound(Path('none.wav'), 'hitsound_don_1p')
            audio.load_sound(Path('none.wav'), 'hitsound_kat_1p')
        if global_data.hit_sound == 0:
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "don.wav", 'hitsound_don_1p')
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "ka.wav", 'hitsound_kat_1p')
            audio.set_sound_pan('hitsound_don_1p', 1.0)
            audio.set_sound_pan('hitsound_kat_1p', 1.0)
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "don_2p.wav", 'hitsound_don_2p')
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "ka_2p.wav", 'hitsound_kat_2p')
            audio.set_sound_pan('hitsound_don_2p', 0.0)
            audio.set_sound_pan('hitsound_kat_2p', 0.0)
        else:
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "don.ogg", 'hitsound_don_1p')
            audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "ka.ogg", 'hitsound_kat_1p')

    def init_tja(self, song: Path, difficulty: int):
        """Initialize the TJA file"""
        self.tja = TJAParser(song, start_delay=self.start_delay, distance=SCREEN_WIDTH - GameScreen.JUDGE_X)
        if self.tja.metadata.bgmovie != Path() and self.tja.metadata.bgmovie.exists():
            self.movie = VideoPlayer(self.tja.metadata.bgmovie)
            self.movie.set_volume(0.0)
        else:
            self.movie = None
        session_data.song_title = self.tja.metadata.title.get(global_data.config['general']['language'].lower(), self.tja.metadata.title['en'])
        if self.tja.metadata.wave.exists() and self.tja.metadata.wave.is_file() and self.song_music is None:
            self.song_music = audio.load_music_stream(self.tja.metadata.wave, 'song')

        tja_copy = copy.deepcopy(self.tja)
        self.player_1 = Player(self.tja, 1, difficulty, False)
        self.player_2 = Player(tja_copy, 2, difficulty-1, True)
        self.start_ms = (get_current_ms() - self.tja.metadata.offset*1000)

    def spawn_ending_anims(self):
        if session_data.result_bad == 0:
            self.player_1.ending_anim = FCAnimation(self.player_1.is_2p)
            self.player_2.ending_anim = FCAnimation(self.player_2.is_2p)
        elif self.player_1.gauge.is_clear:
            self.player_1.ending_anim = ClearAnimation(self.player_1.is_2p)
            self.player_2.ending_anim = ClearAnimation(self.player_2.is_2p)
        elif not self.player_1.gauge.is_clear:
            self.player_1.ending_anim = FailAnimation(self.player_1.is_2p)
            self.player_2.ending_anim = FailAnimation(self.player_2.is_2p)

    def update_background(self, current_time):
        if self.movie is not None:
            self.movie.update()
        else:
            if len(self.player_1.current_bars) > 0:
                self.bpm = self.player_1.bpm
            if self.background is not None:
                self.background.update(current_time, self.bpm, self.player_1.gauge, self.player_2.gauge)

    def draw(self):
        if self.movie is not None:
            self.movie.draw()
        elif self.background is not None:
            self.background.draw()
        self.player_1.draw(self.current_ms, self.start_ms, self.mask_shader)
        self.player_2.draw(self.current_ms, self.start_ms, self.mask_shader)
        self.draw_overlay()
