from typing import override
import pyray as ray
import logging
from libs.animation import Animation
from libs.audio import audio
from libs.background import Background
from libs.file_navigator import Exam
from libs.global_data import global_data
from libs.global_objects import AllNetIcon
from libs.tja import TJAParser
from libs.transition import Transition
from libs.utils import OutlinedText, get_current_ms
from libs.texture import tex
from scenes.game import GameScreen, ResultTransition, SongInfo

logger = logging.getLogger(__name__)

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

class DanGameScreen(GameScreen):
    JUDGE_X = 414

    @override
    def on_screen_start(self):
        self.mask_shader = ray.load_shader("shader/outline.vs", "shader/mask.fs")
        self.current_ms = 0
        self.end_ms = 0
        self.start_delay = 4000
        self.song_started = False
        self.song_music = None
        self.song_index = 0
        tex.unload_textures()
        tex.load_screen_textures('game')
        audio.load_screen_sounds('game')
        if global_data.config["general"]["nijiiro_notes"]:
            # drop original
            if "notes" in tex.textures:
                del tex.textures["notes"]
            # load nijiiro, rename "notes"
            # to leave hardcoded 'notes' in calls below
            tex.load_zip("game", "notes_nijiiro")
            tex.textures["notes"] = tex.textures.pop("notes_nijiiro")
            logger.info("Loaded nijiiro notes textures")
        ray.set_shader_value_texture(self.mask_shader, ray.get_shader_location(self.mask_shader, "texture0"), tex.textures['balloon']['rainbow_mask'].texture)
        ray.set_shader_value_texture(self.mask_shader, ray.get_shader_location(self.mask_shader, "texture1"), tex.textures['balloon']['rainbow'].texture)
        session_data = global_data.session_data[global_data.player_num-1]
        songs = session_data.selected_dan
        self.exams = session_data.selected_dan_exam
        self.total_notes = 0
        for song, genre_index, difficulty in songs:
            notes, branch_m, branch_e, branch_n = song.notes_to_position(difficulty)
            self.total_notes += sum(1 for note in notes.play_notes if note.type < 5)
            for branch in branch_m:
                self.total_notes += sum(1 for note in branch.play_notes if note.type < 5)
            for branch in branch_e:
                self.total_notes += sum(1 for note in branch.play_notes if note.type < 5)
            for branch in branch_n:
                self.total_notes += sum(1 for note in branch.play_notes if note.type < 5)
        song, genre_index, difficulty = songs[self.song_index]
        session_data.selected_difficulty = difficulty
        self.hori_name = OutlinedText(session_data.song_title, 40, ray.WHITE)
        self.init_tja(song.file_path)
        self.color = session_data.dan_color
        self.player_1.is_dan = True
        self.player_1.gauge = DanGauge(str(global_data.player_num), self.total_notes)
        logger.info(f"TJA initialized for song: {song.file_path}")
        self.load_hitsounds()
        self.song_info = SongInfo(song.metadata.title.get(global_data.config["general"]["language"], "en"), genre_index)
        self.result_transition = ResultTransition(4)
        self.bpm = self.tja.metadata.bpm
        self.background = Background(global_data.player_num, self.bpm, scene_preset='DAN')
        self.transition = Transition('', '', is_second=True)
        self.transition.start()
        self.dan_transition = DanTransition()
        self.dan_transition.start()
        self.allnet_indicator = AllNetIcon()

    def change_song(self):
        session_data = global_data.session_data[global_data.player_num-1]
        songs = session_data.selected_dan
        song, genre_index, difficulty = songs[self.song_index]
        session_data.selected_difficulty = difficulty
        self.player_1.difficulty = difficulty
        self.tja = TJAParser(song.file_path, start_delay=self.start_delay, distance=SCREEN_WIDTH - GameScreen.JUDGE_X)
        audio.unload_music_stream(self.song_music)
        self.song_music = None
        self.song_started = False

        if self.tja.metadata.wave.exists() and self.tja.metadata.wave.is_file() and self.song_music is None:
            self.song_music = audio.load_music_stream(self.tja.metadata.wave, 'song')
        self.player_1.tja = self.tja
        self.player_1.reset_chart()
        self.dan_transition.start()
        self.start_ms = (get_current_ms() - self.tja.metadata.offset*1000)

    def update(self):
        super(GameScreen, self).update()
        current_time = get_current_ms()
        self.transition.update(current_time)
        self.current_ms = current_time - self.start_ms
        self.dan_transition.update(current_time)
        self.start_song(current_time)
        self.update_background(current_time)

        if self.song_music is not None:
            audio.update_music_stream(self.song_music)

        self.player_1.update(self.current_ms, current_time, self.background)
        self.song_info.update(current_time)
        self.result_transition.update(current_time)
        if self.result_transition.is_finished and not audio.is_sound_playing('result_transition'):
            logger.info("Result transition finished, moving to RESULT screen")
            return self.on_screen_end('RESULT')
        elif self.current_ms >= self.player_1.end_time + 1000:
            session_data = global_data.session_data[global_data.player_num-1]
            if self.song_index == len(session_data.selected_dan) - 1:
                if self.end_ms != 0:
                    if current_time >= self.end_ms + 1000:
                        if self.player_1.ending_anim is None:
                            self.spawn_ending_anims()
                    if current_time >= self.end_ms + 8533.34:
                        if not self.result_transition.is_started:
                            self.result_transition.start()
                            audio.play_sound('result_transition', 'voice')
                            logger.info("Result transition started and voice played")
                else:
                    self.end_ms = current_time
            else:
                self.song_index += 1
                self.dan_transition.start()
                self.change_song()

        return self.global_keys()

    def draw_dan_info(self):
        tex.draw_texture('dan_info', 'total_notes')
        counter = str(self.total_notes - self.player_1.good_count - self.player_1.ok_count - self.player_1.bad_count)
        self._draw_counter(counter, margin=45, texture='total_notes_counter')

        for i, exam in enumerate(self.exams):
            y_offset = i * 94
            tex.draw_texture('dan_info', 'exam_bg', y=y_offset)
            tex.draw_texture('dan_info', 'exam_overlay_1', y=y_offset)

            # Get progress based on exam type
            progress = self._get_exam_progress(exam) / exam.red
            if exam.range == 'less':
                progress = 1 - progress
            self._draw_progress_bar(progress, y_offset)
            # Draw exam type and counter
            counter = str(exam.red)
            self._draw_counter(counter, margin=22, texture='value_counter', index=0, y=y_offset)
            tex.draw_texture('dan_info', f'exam_{exam.type}', y=y_offset, x=-len(counter)*20)

            if exam.range == 'less':
                tex.draw_texture('dan_info', 'exam_less', y=y_offset)
            elif exam.range == 'more':
                tex.draw_texture('dan_info', 'exam_more', y=y_offset)

            tex.draw_texture('dan_info', 'exam_overlay_2', y=y_offset)
            if exam.range == 'less':
                counter = str(max(0, exam.red - self._get_exam_progress(exam)))
            elif exam.range == 'more':
                counter = str(max(0, self._get_exam_progress(exam)))
            self._draw_counter(counter, margin=22, texture='value_counter', index=1, y=y_offset)
            if exam.type == 'gauge':
                tex.draw_texture('dan_info', 'exam_percent', y=y_offset, index=1)

        tex.draw_texture('dan_info', 'frame', frame=self.color)
        if self.hori_name is not None:
            self.hori_name.draw(outline_color=ray.BLACK, x=154 - (self.hori_name.texture.width//2),
                               y=392, x2=min(self.hori_name.texture.width, 275)-self.hori_name.texture.width)

    def _draw_counter(self, counter, margin, texture, index=None, y=0):
        """Helper to draw digit counters"""
        for j in range(len(counter)):
            kwargs = {'frame': int(counter[j]), 'x': -(len(counter) - j) * margin, 'y': y}
            if index is not None:
                kwargs['index'] = index
            tex.draw_texture('dan_info', texture, **kwargs)

    def _get_exam_progress(self, exam: Exam) -> int:
        """Get progress value based on exam type"""
        type_mapping = {
            'gauge': (self.player_1.gauge.gauge_length / self.player_1.gauge.gauge_max) * 100,
            'judgeperfect': self.player_1.good_count,
            'judgegood': self.player_1.ok_count,
            'judgebad': self.player_1.bad_count,
            'score': self.player_1.score,
            'combo': self.player_1.max_combo
        }
        return int(type_mapping.get(exam.type, 0))

    def _draw_progress_bar(self, progress, y_offset):
        """Draw the progress bar with appropriate color"""
        progress = max(0, progress)  # Clamp to 0 minimum
        progress = min(progress, 1)  # Clamp to 1 maximum

        if progress == 1:
            texture = 'exam_max'
        elif progress >= 0.5:
            texture = 'exam_gold'
        else:
            texture = 'exam_red'

        tex.draw_texture('dan_info', texture, x2=940*progress, y=y_offset)

    @override
    def draw(self):
        self.background.draw()
        self.draw_dan_info()
        self.player_1.draw(self.current_ms, self.start_ms, self.mask_shader, dan_transition=self.dan_transition)
        self.draw_overlay()


class DanTransition:
    def __init__(self):
        self.move = tex.get_animation(26)
        self.is_finished = False

    def start(self):
        self.move.start()
        self.is_finished = False

    def update(self, current_time):
        self.move.update(current_time)
        self.is_finished = self.move.is_finished

    def draw(self):
        tex.draw_texture('dan', 'transition', index=0, x=self.move.attribute, mirror='horizontal')
        tex.draw_texture('dan', 'transition', index=1, x=-self.move.attribute)


class DanGauge:
    """The player's gauge"""
    def __init__(self, player_num: str, total_notes: int):
        self.player_num = player_num
        self.string_diff = "_hard"
        self.gauge_length = 0
        self.previous_length = 0
        self.visual_length = 0
        self.total_notes = total_notes
        self.gauge_max = 89
        self.tamashii_fire_change = tex.get_animation(25)
        self.is_clear = False
        self.is_rainbow = False
        self.gauge_update_anim = tex.get_animation(10)
        self.rainbow_fade_in = None
        self.rainbow_animation = None

    def add_good(self):
        """Adds a good note to the gauge"""
        self.gauge_update_anim.start()
        self.previous_length = int(self.gauge_length)
        self.gauge_length += (1 / (self.total_notes * (self.gauge_max / 100))) * 100
        if self.gauge_length > self.gauge_max:
            self.gauge_length = self.gauge_max

        if int(self.gauge_length * 8) % 8 == 0:
            self.visual_length = int(self.gauge_length * 8)

    def add_ok(self):
        """Adds an ok note to the gauge"""
        self.gauge_update_anim.start()
        self.previous_length = int(self.gauge_length)
        self.gauge_length += (0.5 / (self.total_notes * (self.gauge_max / 100))) * 100
        if self.gauge_length > self.gauge_max:
            self.gauge_length = self.gauge_max

        if int(self.gauge_length * 8) % 8 == 0:
            self.visual_length = int(self.gauge_length * 8)

    def add_bad(self):
        """Adds a bad note to the gauge"""
        self.previous_length = int(self.gauge_length)
        self.gauge_length -= (2 / (self.total_notes * (self.gauge_max / 100))) * 100
        if self.gauge_length < 0:
            self.gauge_length = 0

        if int(self.gauge_length * 8) % 8 == 0:
            self.visual_length = int(self.gauge_length * 8)

    def update(self, current_ms: float):
        self.is_rainbow = self.gauge_length == self.gauge_max
        self.is_clear = self.is_rainbow
        if self.gauge_length == self.gauge_max and self.rainbow_fade_in is None:
            self.rainbow_fade_in = Animation.create_fade(450, initial_opacity=0.0, final_opacity=1.0)
            self.rainbow_fade_in.start()
        self.gauge_update_anim.update(current_ms)
        self.tamashii_fire_change.update(current_ms)

        if self.rainbow_fade_in is not None:
            self.rainbow_fade_in.update(current_ms)

        if self.rainbow_animation is None:
            self.rainbow_animation = Animation.create_texture_change((16.67*8) * 3, textures=[((16.67 * 3) * i, (16.67 * 3) * (i + 1), i) for i in range(8)])
            self.rainbow_animation.start()
        else:
            self.rainbow_animation.update(current_ms)
            if self.rainbow_animation.is_finished or self.gauge_length < 87:
                self.rainbow_animation = None

    def draw(self):
        tex.draw_texture('gauge_dan', 'border')
        tex.draw_texture('gauge_dan', f'{self.player_num}p_unfilled')
        tex.draw_texture('gauge_dan', f'{self.player_num}p_bar', x2=self.visual_length-8)

        # Rainbow effect for full gauge
        if self.gauge_length == self.gauge_max and self.rainbow_fade_in is not None and self.rainbow_animation is not None:
            if 0 < self.rainbow_animation.attribute < 8:
                tex.draw_texture('gauge_dan', 'rainbow', frame=self.rainbow_animation.attribute-1, fade=self.rainbow_fade_in.attribute)
            tex.draw_texture('gauge_dan', 'rainbow', frame=self.rainbow_animation.attribute, fade=self.rainbow_fade_in.attribute)
        if self.gauge_update_anim is not None and self.visual_length <= self.gauge_max and self.visual_length > self.previous_length:
            tex.draw_texture('gauge_dan', f'{self.player_num}p_bar_fade', x=self.visual_length-8, fade=self.gauge_update_anim.attribute)
        tex.draw_texture('gauge_dan', 'overlay', fade=0.15)

        # Draw clear status indicators
        if self.is_rainbow:
            tex.draw_texture('gauge_dan', 'tamashii_fire', scale=0.75, center=True, frame=self.tamashii_fire_change.attribute)
            tex.draw_texture('gauge_dan', 'tamashii')
            if self.is_rainbow and self.tamashii_fire_change.attribute in (0, 1, 4, 5):
                tex.draw_texture('gauge_dan', 'tamashii_overlay', fade=0.5)
        else:
            tex.draw_texture('gauge_dan', 'tamashii_dark')
