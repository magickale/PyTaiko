import bisect
import math
import sqlite3
from collections import deque
from pathlib import Path
from typing import Optional

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.background import Background
from libs.chara_2d import Chara2D
from libs.global_objects import Nameplate
from libs.texture import tex
from libs.tja import (
    Balloon,
    Drumroll,
    Note,
    NoteList,
    TJAParser,
    apply_modifiers,
    calculate_base_score,
)
from libs.transition import Transition
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    global_tex,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
    session_data,
)
from libs.video import VideoPlayer

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

class GameScreen:
    JUDGE_X = 414
    def __init__(self):
        self.current_ms = 0
        self.screen_init = False
        self.end_ms = 0
        self.start_delay = 1000
        self.song_started = False
        self.mask_shader = ray.load_shader("", "shader/mask.fs")

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        if global_data.hit_sound == -1:
            self.sound_don = audio.load_sound(Path('none.wav'))
            self.sound_kat = audio.load_sound(Path('none.wav'))
        if global_data.hit_sound == 0:
            self.sound_don = audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "don.wav")
            self.sound_kat = audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "ka.wav")
        else:
            self.sound_don = audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "don.ogg")
            self.sound_kat = audio.load_sound(sounds_dir / "hit_sounds" / str(global_data.hit_sound) / "ka.ogg")
        self.sound_restart = audio.load_sound(sounds_dir / 'song_select' / 'Skip.ogg')
        self.sound_balloon_pop = audio.load_sound(sounds_dir / "balloon_pop.wav")
        self.sound_kusudama_pop = audio.load_sound(sounds_dir / "kusudama_pop.ogg")
        self.sound_result_transition = audio.load_sound(sounds_dir / "result" / "VO_RESULT [1].ogg")

    def init_tja(self, song: Path, difficulty: int):
        if song == Path(''):
            self.start_ms = get_current_ms()
            self.tja = None
        else:
            self.tja = TJAParser(song, start_delay=self.start_delay, distance=SCREEN_WIDTH - GameScreen.JUDGE_X)
            if self.tja.metadata.bgmovie != Path() and self.tja.metadata.bgmovie.exists():
                self.movie = VideoPlayer(self.tja.metadata.bgmovie)
                self.movie.set_volume(0.0)
            else:
                self.movie = None
            session_data.song_title = self.tja.metadata.title.get(global_data.config['general']['language'].lower(), self.tja.metadata.title['en'])
            if self.tja.metadata.wave.exists() and self.tja.metadata.wave.is_file() and self.song_music is None:
                self.song_music = audio.load_music_stream(self.tja.metadata.wave)
                audio.normalize_music_stream(self.song_music, 0.1935)

        self.player_1 = Player(self.tja, global_data.player_num, difficulty)
        if self.tja is not None:
            self.start_ms = (get_current_ms() - self.tja.metadata.offset*1000)

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True
            self.movie = None
            self.song_music = None
            tex.load_screen_textures('game')
            ray.set_shader_value_texture(self.mask_shader, ray.get_shader_location(self.mask_shader, "texture0"), tex.textures['balloon']['rainbow_mask'].texture)
            ray.set_shader_value_texture(self.mask_shader, ray.get_shader_location(self.mask_shader, "texture1"), tex.textures['balloon']['rainbow'].texture)
            self.load_sounds()
            self.init_tja(global_data.selected_song, session_data.selected_difficulty)
            self.song_info = SongInfo(session_data.song_title, session_data.genre_index)
            self.result_transition = ResultTransition(global_data.player_num)
            self.bpm = 120
            if self.tja is not None:
                subtitle = self.tja.metadata.subtitle.get(global_data.config['general']['language'].lower(), '')
                self.bpm = self.tja.metadata.bpm
                scene_preset = self.tja.metadata.scene_preset
            else:
                subtitle = ''
                scene_preset = ''
            self.background = Background(global_data.player_num, self.bpm, scene_preset=scene_preset)
            self.transition = Transition(session_data.song_title, subtitle, is_second=True)
            self.transition.start()

    def on_screen_end(self, next_screen):
        self.screen_init = False
        tex.unload_textures()
        if self.song_music is not None:
            audio.unload_music_stream(self.song_music)
        self.song_started = False
        self.end_ms = 0
        self.movie = None
        if self.background is not None:
            self.background.unload()
        return next_screen

    def write_score(self):
        if self.tja is None:
            return
        if global_data.modifiers.auto:
            return
        with sqlite3.connect('scores.db') as con:
            cursor = con.cursor()
            notes, _, _, _ = TJAParser.notes_to_position(TJAParser(self.tja.file_path), self.player_1.difficulty)
            hash = self.tja.hash_note_data(notes)
            check_query = "SELECT score FROM Scores WHERE hash = ? LIMIT 1"
            cursor.execute(check_query, (hash,))
            result = cursor.fetchone()
            if result is None or session_data.result_score > result[0]:
                if result is None:
                    session_data.prev_score = 0
                else:
                    session_data.prev_score = result[0]
                insert_query = '''
                INSERT OR REPLACE INTO Scores (hash, en_name, jp_name, diff, score, good, ok, bad, drumroll, combo, clear)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                '''
                data = (hash, self.tja.metadata.title['en'],
                        self.tja.metadata.title.get('ja', ''), self.player_1.difficulty,
                        session_data.result_score, session_data.result_good,
                        session_data.result_ok, session_data.result_bad,
                        session_data.result_total_drumroll, session_data.result_max_combo, int(self.player_1.gauge.is_clear))
                cursor.execute(insert_query, data)
                con.commit()

    def update(self):
        self.on_screen_start()
        current_time = get_current_ms()
        self.transition.update(current_time)
        self.current_ms = current_time - self.start_ms
        if self.tja is not None:
            if (self.current_ms >= self.tja.metadata.offset*1000 + self.start_delay - global_data.config["general"]["judge_offset"]) and not self.song_started:
                if self.song_music is not None:
                    audio.play_music_stream(self.song_music)
                    print(f"Song started at {self.current_ms}")
                if self.movie is not None:
                    self.movie.start(current_time)
                self.song_started = True
        if self.movie is not None:
            self.movie.update()
        else:
            if len(self.player_1.current_bars) > 0:
                self.bpm = self.player_1.bpm
            if self.background is not None:
                self.background.update(current_time, self.bpm, self.player_1.gauge)

        if self.song_music is not None:
            audio.update_music_stream(self.song_music)

        self.player_1.update(self, current_time)
        self.song_info.update(current_time)
        self.result_transition.update(current_time)
        if self.result_transition.is_finished:
            return self.on_screen_end('RESULT')
        elif len(self.player_1.don_notes) == 0 and len(self.player_1.kat_notes) == 0 and len(self.player_1.other_notes) == 0:
            session_data.result_score, session_data.result_good, session_data.result_ok, session_data.result_bad, session_data.result_max_combo, session_data.result_total_drumroll = self.player_1.get_result_score()
            session_data.result_gauge_length = self.player_1.gauge.gauge_length
            if self.end_ms != 0:
                if current_time >= self.end_ms + 8533.34:
                    if not self.result_transition.is_started:
                        self.result_transition.start()
                        audio.play_sound(self.sound_result_transition)
            else:
                self.write_score()
                self.end_ms = current_time

        if ray.is_key_pressed(ray.KeyboardKey.KEY_F1):
            if self.song_music is not None:
                audio.stop_music_stream(self.song_music)
            self.init_tja(global_data.selected_song, session_data.selected_difficulty)
            audio.play_sound(self.sound_restart)
            self.song_started = False

        if ray.is_key_pressed(ray.KeyboardKey.KEY_ESCAPE):
            if self.song_music is not None:
                audio.stop_music_stream(self.song_music)
            return self.on_screen_end('SONG_SELECT')

    def draw(self):
        if self.movie is not None:
            self.movie.draw()
        elif self.background is not None:
            self.background.draw()
        self.player_1.draw(self)
        self.song_info.draw()
        self.transition.draw()
        self.result_transition.draw()

    def draw_3d(self):
        self.player_1.draw_3d()

class Player:
    TIMING_GOOD = 25.0250015258789
    TIMING_OK = 75.0750045776367
    TIMING_BAD = 108.441665649414

    TIMING_GOOD_EASY = 41.7083358764648
    TIMING_OK_EASY = 108.441665649414
    TIMING_BAD_EASY = 125.125

    def __init__(self, tja: Optional[TJAParser], player_number: int, difficulty: int):

        self.player_number = str(player_number)
        self.difficulty = difficulty
        self.visual_offset = global_data.config["general"]["visual_offset"]

        if tja is not None:
            notes, self.branch_m, self.branch_e, self.branch_n = tja.notes_to_position(self.difficulty)
            self.play_notes, self.draw_note_list, self.draw_bar_list = apply_modifiers(notes)
        else:
            self.play_notes, self.draw_note_list, self.draw_bar_list = deque(), deque(), deque()
            notes = NoteList()

        self.don_notes = deque([note for note in self.play_notes if note.type in {1, 3}])
        self.kat_notes = deque([note for note in self.play_notes if note.type in {2, 4}])
        self.other_notes = deque([note for note in self.play_notes if note.type not in {1, 2, 3, 4}])
        self.total_notes = len([note for note in self.play_notes if 0 < note.type < 5])
        total_notes = notes
        if self.branch_m:
            for section in self.branch_m:
                self.total_notes += len([note for note in section.play_notes if 0 < note.type < 5])
                total_notes += section
        self.base_score = calculate_base_score(total_notes)

        #Note management
        self.current_bars: list[Note] = []
        self.current_notes_draw: list[Note | Drumroll | Balloon] = []
        self.is_drumroll = False
        self.curr_drumroll_count = 0
        self.is_balloon = False
        self.curr_balloon_count = 0
        self.is_branch = False
        self.curr_branch_reqs = []
        self.branch_condition_count = 0
        self.branch_condition = ''
        self.balloon_index = 0
        self.bpm = self.play_notes[0].bpm if self.play_notes else 120

        #Score management
        self.good_count = 0
        self.ok_count = 0
        self.bad_count = 0
        self.combo = 0
        self.score = 0
        self.max_combo = 0
        self.total_drumroll = 0

        self.arc_points = 25

        self.draw_judge_list: list[Judgement] = []
        self.lane_hit_effect: Optional[LaneHitEffect] = None
        self.draw_arc_list: list[NoteArc] = []
        self.draw_drum_hit_list: list[DrumHitEffect] = []
        self.drumroll_counter: Optional[DrumrollCounter] = None
        self.balloon_anim: Optional[BalloonAnimation] = None
        self.kusudama_anim: Optional[KusudamaAnimation] = None
        self.base_score_list: list[ScoreCounterAnimation] = []
        self.combo_display = Combo(self.combo, 0)
        self.score_counter = ScoreCounter(self.score)
        self.gogo_time: Optional[GogoTime] = None
        self.combo_announce = ComboAnnounce(self.combo, 0)
        self.branch_indicator = BranchIndicator() if tja and tja.metadata.course_data[self.difficulty].is_branching else None
        self.is_gogo_time = False
        plate_info = global_data.config['nameplate']
        self.nameplate = Nameplate(plate_info['name'], plate_info['title'], global_data.player_num, plate_info['dan'], plate_info['gold'])
        self.chara = Chara2D(player_number - 1, self.bpm)

        self.input_log: dict[float, tuple] = dict()

        if tja is not None:
            stars = tja.metadata.course_data[self.difficulty].level
        else:
            stars = 0
        self.gauge = Gauge(self.player_number, self.difficulty, stars, self.total_notes)
        self.gauge_hit_effect: list[GaugeHitEffect] = []

        self.autoplay_hit_side = 'L'
        self.last_subdivision = -1

    def merge_branch_section(self, branch_section: NoteList, current_ms: float):
        self.play_notes.extend(branch_section.play_notes)
        self.draw_note_list.extend(branch_section.draw_notes)
        self.draw_bar_list.extend(branch_section.bars)
        self.play_notes = deque(sorted(self.play_notes))
        self.draw_note_list = deque(sorted(self.draw_note_list, key=lambda x: x.load_ms))
        self.draw_bar_list = deque(sorted(self.draw_bar_list, key=lambda x: x.load_ms))
        timing_threshold = current_ms - Player.TIMING_BAD
        total_don = [note for note in self.play_notes if note.type in {1, 3}]
        total_kat = [note for note in self.play_notes if note.type in {2, 4}]
        total_other = [note for note in self.play_notes if note.type not in {1, 2, 3, 4}]

        self.don_notes = deque([note for note in total_don if note.hit_ms > timing_threshold])
        self.kat_notes = deque([note for note in total_kat if note.hit_ms > timing_threshold])
        self.other_notes = deque([note for note in total_other if note.hit_ms > timing_threshold])

    def get_result_score(self):
        return self.score, self.good_count, self.ok_count, self.bad_count, self.max_combo, self.total_drumroll

    def get_position_x(self, width: int, current_ms: float, load_ms: float, pixels_per_frame: float) -> int:
        time_diff = load_ms - current_ms
        return int(width + pixels_per_frame * 0.06 * time_diff - 64) - self.visual_offset

    def get_position_y(self, current_ms: float, load_ms: float, pixels_per_frame: float, pixels_per_frame_x) -> int:
        time_diff = load_ms - current_ms
        return int((pixels_per_frame * 0.06 * time_diff) + ((866 * pixels_per_frame) / pixels_per_frame_x))

    def animation_manager(self, animation_list: list, current_time: float):
        if not animation_list:
            return

        # More efficient: use list comprehension to filter out finished animations
        remaining_animations = []
        for animation in animation_list:
            animation.update(current_time)
            if not animation.is_finished:
                remaining_animations.append(animation)

        # Replace the original list contents
        animation_list[:] = remaining_animations

    def bar_manager(self, current_ms: float):
        #Add bar to current_bars list if it is ready to be shown on screen
        if self.draw_bar_list and current_ms > self.draw_bar_list[0].load_ms:
            self.current_bars.append(self.draw_bar_list.popleft())

        #If a bar is off screen, remove it
        if not self.current_bars:
            return

        # More efficient removal with early exit
        removal_threshold = GameScreen.JUDGE_X + 650
        bars_to_keep = []
        for bar in self.current_bars:
            position = self.get_position_x(SCREEN_WIDTH, current_ms, bar.hit_ms, bar.pixels_per_frame_x)
            if position >= removal_threshold:
                bars_to_keep.append(bar)
        self.current_bars = bars_to_keep
        if self.current_bars and hasattr(self.current_bars[-1], 'branch_params'):
            self.branch_condition, e_req, m_req = self.current_bars[-1].branch_params.split(',')
            delattr(self.current_bars[-1], 'branch_params')
            e_req = int(e_req)
            m_req = int(m_req)
            if not self.is_branch:
                self.is_branch = True
                if self.branch_condition == 'r':
                    end_time = self.branch_m[0].bars[0].load_ms
                    end_roll = -1

                    note_lists = [
                        self.current_notes_draw,
                        self.branch_n[0].draw_notes if self.branch_n else [],
                        self.branch_e[0].draw_notes if self.branch_e else [],
                        self.branch_m[0].draw_notes if self.branch_m else [],
                        self.draw_note_list if self.draw_note_list else []
                    ]

                    end_roll = -1
                    for notes in note_lists:
                        for i in range(len(notes)-1, -1, -1):
                            if notes[i].type == 8 and notes[i].hit_ms <= end_time:
                                end_roll = notes[i].hit_ms
                                break
                        if end_roll != -1:
                            break
                    self.curr_branch_reqs = [e_req, m_req, end_roll, 0]
                elif self.branch_condition == 'p':
                    start_time = self.current_bars[0].hit_ms if self.current_bars else self.current_bars[-1].hit_ms
                    branch_start_time = self.branch_m[0].bars[0].load_ms

                    note_lists = [
                        self.current_notes_draw,
                        self.branch_n[0].draw_notes if self.branch_n else [],
                        self.branch_e[0].draw_notes if self.branch_e else [],
                        self.branch_m[0].draw_notes if self.branch_m else [],
                        self.draw_note_list if self.draw_note_list else []
                    ]

                    seen_notes = set()
                    for notes in note_lists:
                        for note in notes:
                            if note.type <= 4 and start_time <= note.hit_ms < branch_start_time:
                                seen_notes.add(note)

                    self.curr_branch_reqs = [e_req, m_req, branch_start_time, len(seen_notes)]
    def play_note_manager(self, current_ms: float, background: Optional[Background]):
        if self.don_notes and self.don_notes[0].hit_ms + Player.TIMING_BAD < current_ms:
            self.combo = 0
            if background is not None:
                background.add_chibi(True)
            self.bad_count += 1
            self.gauge.add_bad()
            self.don_notes.popleft()
            if self.is_branch and self.branch_condition == 'p':
                self.branch_condition_count -= 1

        if self.kat_notes and self.kat_notes[0].hit_ms + Player.TIMING_BAD < current_ms:
            self.combo = 0
            if background is not None:
                background.add_chibi(True)
            self.bad_count += 1
            self.gauge.add_bad()
            self.kat_notes.popleft()
            if self.is_branch and self.branch_condition == 'p':
                self.branch_condition_count -= 1

        if not self.other_notes:
            return

        note = self.other_notes[0]
        if note.hit_ms + Player.TIMING_BAD < current_ms:
            if note.type != 8:
                if len(self.other_notes) > 1:
                    tail = self.other_notes[1]
                    if tail.hit_ms <= current_ms:
                        self.other_notes.popleft()
                        self.other_notes.popleft()
                        self.is_drumroll = False
                        self.is_balloon = False
            else:
                if len(self.other_notes) == 1:
                    self.other_notes.popleft()
        elif (note.hit_ms <= current_ms):
            if note.type == 5 or note.type == 6:
                self.is_drumroll = True
            elif note.type == 7 or note.type == 9:
                self.is_balloon = True

    def draw_note_manager(self, current_ms: float):
        if self.draw_note_list and current_ms + 1000 >= self.draw_note_list[0].load_ms:
            current_note = self.draw_note_list.popleft()
            if 5 <= current_note.type <= 7:
                bisect.insort_left(self.current_notes_draw, current_note, key=lambda x: x.index)
                try:
                    tail_note = next((note for note in self.draw_note_list if note.type == 8))
                    bisect.insort_left(self.current_notes_draw, tail_note, key=lambda x: x.index)
                    self.draw_note_list.remove(tail_note)
                except Exception as e:
                    raise(e)
            else:
                bisect.insort_left(self.current_notes_draw, current_note, key=lambda x: x.index)

        if not self.current_notes_draw:
            return

        if isinstance(self.current_notes_draw[0], Drumroll) and 255 > self.current_notes_draw[0].color > 0:
            self.current_notes_draw[0].color += 1

        note = self.current_notes_draw[0]
        if note.type in {5, 6, 7} and len(self.current_notes_draw) > 1:
            note = self.current_notes_draw[1]
        position = self.get_position_x(SCREEN_WIDTH, current_ms, note.hit_ms, note.pixels_per_frame_x)
        if position < GameScreen.JUDGE_X + 650:
            self.current_notes_draw.pop(0)

    def note_manager(self, current_ms: float, background: Optional[Background], current_time: float):
        self.bar_manager(current_ms)
        self.play_note_manager(current_ms, background)
        self.draw_note_manager(current_ms)

    def note_correct(self, note: Note, current_time: float):

        # Remove from the appropriate separated list
        if note.type in {1, 3} and self.don_notes and self.don_notes[0] == note:
            self.don_notes.popleft()
        elif note.type in {2, 4} and self.kat_notes and self.kat_notes[0] == note:
            self.kat_notes.popleft()
        elif note.type not in {1, 2, 3, 4} and self.other_notes and self.other_notes[0] == note:
            self.other_notes.popleft()

        index = note.index
        if note.type == 7:
            if self.other_notes:
                self.other_notes.popleft()

        if note.type < 7:
            self.combo += 1
            if self.combo % 10 == 0:
                self.chara.set_animation('10_combo')
            if self.combo % 100 == 0:
                self.combo_announce = ComboAnnounce(self.combo, current_time)
            if self.combo > self.max_combo:
                self.max_combo = self.combo

        if note.type != 9:
            self.draw_arc_list.append(NoteArc(note.type, current_time, 1, note.type == 3 or note.type == 4 or note.type == 7, note.type == 7))

        if note in self.current_notes_draw:
            index = self.current_notes_draw.index(note)
            self.current_notes_draw.pop(index)

    def check_drumroll(self, drum_type: int, background: Optional[Background], current_time: float):
        self.draw_arc_list.append(NoteArc(drum_type, current_time, 1, drum_type == 3 or drum_type == 4, False))
        self.curr_drumroll_count += 1
        self.total_drumroll += 1
        if self.is_branch and self.branch_condition == 'r':
            self.branch_condition_count += 1
        if background is not None:
            background.add_renda()
        self.score += 100
        self.base_score_list.append(ScoreCounterAnimation(self.player_number, 100))
        if not isinstance(self.current_notes_draw[0], Drumroll):
            return
        self.current_notes_draw[0].color = max(0, 255 - (self.curr_drumroll_count * 10))

    def check_balloon(self, game_screen: GameScreen, drum_type: int, note: Balloon, current_time: float):
        if drum_type != 1:
            return
        if note.is_kusudama:
            self.check_kusudama(game_screen, note)
            return
        if self.balloon_anim is None:
            self.balloon_anim = BalloonAnimation(current_time, note.count)
        self.curr_balloon_count += 1
        self.total_drumroll += 1
        self.score += 100
        self.base_score_list.append(ScoreCounterAnimation(self.player_number, 100))
        if self.curr_balloon_count == note.count:
            self.is_balloon = False
            note.popped = True
            self.balloon_anim.update(current_time, self.curr_balloon_count, note.popped)
            audio.play_sound(game_screen.sound_balloon_pop)
            self.note_correct(note, current_time)
            self.curr_balloon_count = 0

    def check_kusudama(self, game_screen: GameScreen, note: Balloon):
        if self.kusudama_anim is None:
            self.kusudama_anim = KusudamaAnimation(note.count)
        self.curr_balloon_count += 1
        self.total_drumroll += 1
        self.score += 100
        self.base_score_list.append(ScoreCounterAnimation(self.player_number, 100))
        if self.curr_balloon_count == note.count:
            audio.play_sound(game_screen.sound_kusudama_pop)
            self.is_balloon = False
            note.popped = True
            self.curr_balloon_count = 0

    def check_note(self, game_screen: GameScreen, drum_type: int, current_time: float):
        if len(self.don_notes) == 0 and len(self.kat_notes) == 0 and len(self.other_notes) == 0:
            return

        if self.difficulty < 2:
            good_window_ms = Player.TIMING_GOOD_EASY
            ok_window_ms = Player.TIMING_OK_EASY
            bad_window_ms = Player.TIMING_BAD_EASY
        else:
            good_window_ms = Player.TIMING_GOOD
            ok_window_ms = Player.TIMING_OK
            bad_window_ms = Player.TIMING_BAD

        curr_note = self.other_notes[0] if self.other_notes else None
        if self.is_drumroll:
            self.check_drumroll(drum_type, game_screen.background, current_time)
        elif self.is_balloon:
            if not isinstance(curr_note, Balloon):
                raise Exception("Balloon mode entered but current note is not balloon")
            self.check_balloon(game_screen, drum_type, curr_note, current_time)
        else:
            self.curr_drumroll_count = 0

            if drum_type == 1:
                if not self.don_notes:
                    return
                curr_note = self.don_notes[0]
            elif drum_type == 2:
                if not self.kat_notes:
                    return
                curr_note = self.kat_notes[0]
            else:
                return

            #If the note is too far away, stop checking
            if game_screen.current_ms > (curr_note.hit_ms + bad_window_ms):
                return

            big = curr_note.type == 3 or curr_note.type == 4
            if (curr_note.hit_ms - good_window_ms) <= game_screen.current_ms <= (curr_note.hit_ms + good_window_ms):
                self.draw_judge_list.append(Judgement('GOOD', big, ms_display=game_screen.current_ms - curr_note.hit_ms))
                self.lane_hit_effect = LaneHitEffect('GOOD')
                self.good_count += 1
                self.score += self.base_score
                self.base_score_list.append(ScoreCounterAnimation(self.player_number, self.base_score))
                self.note_correct(curr_note, current_time)
                self.gauge.add_good()
                if self.is_branch and self.branch_condition == 'p':
                    self.branch_condition_count += 1
                if game_screen.background is not None:
                    game_screen.background.add_chibi(False)

            elif (curr_note.hit_ms - ok_window_ms) <= game_screen.current_ms <= (curr_note.hit_ms + ok_window_ms):
                self.draw_judge_list.append(Judgement('OK', big, ms_display=game_screen.current_ms - curr_note.hit_ms))
                self.ok_count += 1
                self.score += 10 * math.floor(self.base_score / 2 / 10)
                self.base_score_list.append(ScoreCounterAnimation(self.player_number, 10 * math.floor(self.base_score / 2 / 10)))
                self.note_correct(curr_note, current_time)
                self.gauge.add_ok()
                if self.is_branch and self.branch_condition == 'p':
                    self.branch_condition_count += 0.5
                if game_screen.background is not None:
                    game_screen.background.add_chibi(False)

            elif (curr_note.hit_ms - bad_window_ms) <= game_screen.current_ms <= (curr_note.hit_ms + bad_window_ms):
                self.draw_judge_list.append(Judgement('BAD', big, ms_display=game_screen.current_ms - curr_note.hit_ms))
                self.bad_count += 1
                self.combo = 0
                # Remove from both the specific note list and the main play_notes list
                if drum_type == 1:
                    self.don_notes.popleft()
                else:
                    self.kat_notes.popleft()
                self.gauge.add_bad()
                if game_screen.background is not None:
                    game_screen.background.add_chibi(True)

    def drumroll_counter_manager(self, current_time: float):
        if self.is_drumroll and self.curr_drumroll_count > 0 and self.drumroll_counter is None:
            self.drumroll_counter = DrumrollCounter(current_time)

        if self.drumroll_counter is not None:
            if self.drumroll_counter.is_finished and not self.is_drumroll:
                self.drumroll_counter = None
            else:
                self.drumroll_counter.update(current_time, self.curr_drumroll_count)

    def balloon_manager(self, current_time: float):
        if self.balloon_anim is not None:
            self.chara.set_animation('balloon_popping')
            self.balloon_anim.update(current_time, self.curr_balloon_count, not self.is_balloon)
            if self.balloon_anim.is_finished:
                self.balloon_anim = None
                self.chara.set_animation('balloon_pop')
        if self.kusudama_anim is not None:
            self.kusudama_anim.update(current_time, not self.is_balloon)
            self.kusudama_anim.update_count(self.curr_balloon_count)
            if self.kusudama_anim.is_finished:
                self.kusudama_anim = None

    def handle_input(self, game_screen: GameScreen, current_time: float):
        input_checks = [
            (is_l_don_pressed, 'DON', 'L', game_screen.sound_don),
            (is_r_don_pressed, 'DON', 'R', game_screen.sound_don),
            (is_l_kat_pressed, 'KAT', 'L', game_screen.sound_kat),
            (is_r_kat_pressed, 'KAT', 'R', game_screen.sound_kat)
        ]
        for check_func, note_type, side, sound in input_checks:
            if check_func():
                self.lane_hit_effect = LaneHitEffect(note_type)
                self.draw_drum_hit_list.append(DrumHitEffect(note_type, side))

                audio.play_sound(sound)

                drum_value = 1 if note_type == 'DON' else 2
                self.check_note(game_screen, drum_value, current_time)
                self.input_log[game_screen.current_ms] = (note_type, side)

    def autoplay_manager(self, game_screen: GameScreen, current_time: float):
        if not global_data.modifiers.auto:
            return

        # Handle drumroll and balloon hits
        if self.is_drumroll or self.is_balloon:
            if not self.other_notes:
                return
            note = self.other_notes[0]
            bpm = note.bpm
            if bpm == 0:
                subdivision_in_ms = 0
            else:
                subdivision_in_ms = game_screen.current_ms // ((60000 * 4 / bpm) / 24)
            if subdivision_in_ms > self.last_subdivision:
                self.last_subdivision = subdivision_in_ms
                hit_type = 'DON'
                self.lane_hit_effect = LaneHitEffect(hit_type)
                self.autoplay_hit_side = 'R' if self.autoplay_hit_side == 'L' else 'L'
                self.draw_drum_hit_list.append(DrumHitEffect(hit_type, self.autoplay_hit_side))
                audio.play_sound(game_screen.sound_don)
                note_type = 3 if note.type == 6 else 1
                self.check_note(game_screen, note_type, current_time)
        else:
            # Handle DON notes
            while self.don_notes and game_screen.current_ms >= self.don_notes[0].hit_ms:
                note = self.don_notes[0]
                hit_type = 'DON'
                self.lane_hit_effect = LaneHitEffect(hit_type)
                self.autoplay_hit_side = 'R' if self.autoplay_hit_side == 'L' else 'L'
                self.draw_drum_hit_list.append(DrumHitEffect(hit_type, self.autoplay_hit_side))
                audio.play_sound(game_screen.sound_don)
                self.check_note(game_screen, 1, current_time)

            # Handle KAT notes
            while self.kat_notes and game_screen.current_ms >= self.kat_notes[0].hit_ms:
                note = self.kat_notes[0]
                hit_type = 'KAT'
                self.lane_hit_effect = LaneHitEffect(hit_type)
                self.autoplay_hit_side = 'R' if self.autoplay_hit_side == 'L' else 'L'
                self.draw_drum_hit_list.append(DrumHitEffect(hit_type, self.autoplay_hit_side))
                audio.play_sound(game_screen.sound_kat)
                self.check_note(game_screen, 2, current_time)

    def evaluate_branch(self, current_ms):
        e_req, m_req, end_time, total_notes = self.curr_branch_reqs
        if current_ms >= end_time:
            self.is_branch = False
            if self.branch_condition == 'p':
                self.branch_condition_count = min(int((self.branch_condition_count/total_notes)*100), 100)
            if self.branch_condition_count >= e_req and self.branch_condition_count < m_req:
                self.merge_branch_section(self.branch_e.pop(0), current_ms)
                if self.branch_indicator is not None and self.branch_indicator.difficulty != 'expert':
                    if self.branch_indicator.difficulty == 'master':
                        self.branch_indicator.level_down('expert')
                    else:
                        self.branch_indicator.level_up('expert')
                self.branch_m.pop(0)
                self.branch_n.pop(0)
            elif self.branch_condition_count >= m_req:
                self.merge_branch_section(self.branch_m.pop(0), current_ms)
                if self.branch_indicator is not None and self.branch_indicator.difficulty != 'master':
                    self.branch_indicator.level_up('master')
                self.branch_n.pop(0)
                self.branch_e.pop(0)
            else:
                self.merge_branch_section(self.branch_n.pop(0), current_ms)
                if self.branch_indicator is not None and self.branch_indicator.difficulty != 'normal':
                    self.branch_indicator.level_down('normal')
                self.branch_m.pop(0)
                self.branch_e.pop(0)
            self.branch_condition_count = 0

    def update(self, game_screen: GameScreen, current_time: float):
        self.note_manager(game_screen.current_ms, game_screen.background, current_time)
        self.combo_display.update(current_time, self.combo)
        self.combo_announce.update(current_time)
        self.drumroll_counter_manager(current_time)
        self.animation_manager(self.draw_judge_list, current_time)
        self.balloon_manager(current_time)
        if self.gogo_time is not None:
            self.gogo_time.update(current_time)
        if self.lane_hit_effect is not None:
            self.lane_hit_effect.update(current_time)
        self.animation_manager(self.draw_drum_hit_list, current_time)

        # More efficient arc management
        finished_arcs = []
        for i, anim in enumerate(self.draw_arc_list):
            anim.update(current_time)
            if anim.is_finished:
                self.gauge_hit_effect.append(GaugeHitEffect(anim.note_type, anim.is_big))
                finished_arcs.append(i)
        for i in reversed(finished_arcs):
            self.draw_arc_list.pop(i)

        self.animation_manager(self.gauge_hit_effect, current_time)
        self.animation_manager(self.base_score_list, current_time)
        self.score_counter.update(current_time, self.score)
        self.autoplay_manager(game_screen, current_time)
        self.handle_input(game_screen, current_time)
        self.nameplate.update(current_time)
        self.gauge.update(current_time)
        if self.branch_indicator is not None:
            self.branch_indicator.update(current_time)

        if self.is_branch:
            self.evaluate_branch(game_screen.current_ms)

        # Get the next note from any of the three lists for BPM and gogo time updates
        next_note = None
        if self.don_notes:
            next_note = self.don_notes[0]
        elif self.kat_notes:
            next_note = self.kat_notes[0]
        elif self.other_notes:
            next_note = self.other_notes[0]

        if next_note:
            self.bpm = next_note.bpm
            if next_note.gogo_time and not self.is_gogo_time:
                self.is_gogo_time = True
                self.gogo_time = GogoTime()
                self.chara.set_animation('gogo_start')
            if not next_note.gogo_time and self.is_gogo_time:
                self.is_gogo_time = False
                self.gogo_time = None
                self.chara.set_animation('gogo_stop')
        self.chara.update(current_time, self.bpm, self.gauge.is_clear, self.gauge.is_rainbow)

    def draw_drumroll(self, current_ms: float, head: Drumroll, current_eighth: int):
        start_position = self.get_position_x(SCREEN_WIDTH, current_ms, head.load_ms, head.pixels_per_frame_x)
        tail = next((note for note in self.current_notes_draw[1:] if note.type == 8 and note.index > head.index), self.current_notes_draw[1])
        is_big = int(head.type == 6)
        end_position = self.get_position_x(SCREEN_WIDTH, current_ms, tail.load_ms, tail.pixels_per_frame_x)
        length = end_position - start_position
        color = ray.Color(255, head.color, head.color, 255)
        if head.display:
            if length > 0:
                tex.draw_texture('notes', "8", frame=is_big, x=start_position+64, y=192, x2=length-47, color=color)
                if is_big:
                    tex.draw_texture('notes', "drumroll_big_tail", x=end_position+64, y=192, color=color)
                else:
                    tex.draw_texture('notes', "drumroll_tail", x=end_position+64, y=192, color=color)
            tex.draw_texture('notes', str(head.type), frame=current_eighth % 2, x=start_position, y=192, color=color)

        tex.draw_texture('notes', 'moji_drumroll_mid', x=start_position + 60, y=323, x2=length)
        tex.draw_texture('notes', 'moji', frame=head.moji, x=(start_position - (168//2)) + 64, y=323)
        tex.draw_texture('notes', 'moji', frame=tail.moji, x=(end_position - (168//2)) + 32, y=323)

    def draw_balloon(self, current_ms: float, head: Balloon, current_eighth: int):
        offset = 12
        start_position = self.get_position_x(SCREEN_WIDTH, current_ms, head.load_ms, head.pixels_per_frame_x)
        tail = next((note for note in self.current_notes_draw[1:] if note.type == 8 and note.index > head.index), self.current_notes_draw[1])
        end_position = self.get_position_x(SCREEN_WIDTH, current_ms, tail.load_ms, tail.pixels_per_frame_x)
        pause_position = 349
        if current_ms >= tail.hit_ms:
            position = end_position
        elif current_ms >= head.hit_ms:
            position = pause_position
        else:
            position = start_position
        if head.display:
            tex.draw_texture('notes', str(head.type), frame=current_eighth % 2, x=position-offset, y=192)
        tex.draw_texture('notes', '10', frame=current_eighth % 2, x=position-offset+128, y=192)

    def draw_bars(self, current_ms: float):
        if not self.current_bars:
            return

        # Batch bar draws by pre-calculating positions
        bar_draws = []
        for bar in reversed(self.current_bars):
            if not bar.display:
                continue
            x_position = self.get_position_x(SCREEN_WIDTH, current_ms, bar.load_ms, bar.pixels_per_frame_x)
            y_position = self.get_position_y(current_ms, bar.load_ms, bar.pixels_per_frame_y, bar.pixels_per_frame_x)
            if hasattr(bar, 'is_branch_start'):
                frame = 1
            else:
                frame = 0
            bar_draws.append((str(bar.type), frame, x_position+60, y_position+190))

        # Draw all bars in one batch
        for bar_type, frame, x, y in bar_draws:
            tex.draw_texture('notes', bar_type, frame=frame, x=x, y=y)

    def draw_notes(self, current_ms: float, start_ms: float):
        if not self.current_notes_draw:
            return

        eighth_in_ms = 0 if self.bpm == 0 else (60000 * 4 / self.bpm) / 8
        current_eighth = 0
        if self.combo >= 50 and eighth_in_ms != 0:
            current_eighth = int((current_ms - start_ms) // eighth_in_ms)

        for note in reversed(self.current_notes_draw):
            if self.is_balloon and note == self.current_notes_draw[0]:
                continue
            if note.type == 8:
                continue

            if isinstance(note, Drumroll):
                self.draw_drumroll(current_ms, note, current_eighth)
            elif isinstance(note, Balloon) and not note.is_kusudama:
                x_position = self.get_position_x(SCREEN_WIDTH, current_ms, note.load_ms, note.pixels_per_frame_x)
                y_position = self.get_position_y(current_ms, note.load_ms, note.pixels_per_frame_y, note.pixels_per_frame_x)
                self.draw_balloon(current_ms, note, current_eighth)
                tex.draw_texture('notes', 'moji', frame=note.moji, x=x_position - (168//2) + 64, y=323 + y_position)
            else:
                x_position = self.get_position_x(SCREEN_WIDTH, current_ms, note.load_ms, note.pixels_per_frame_x)
                y_position = self.get_position_y(current_ms, note.load_ms, note.pixels_per_frame_y, note.pixels_per_frame_x)
                if note.display:
                    tex.draw_texture('notes', str(note.type), frame=current_eighth % 2, x=x_position, y=y_position+192, center=True)
                tex.draw_texture('notes', 'moji', frame=note.moji, x=x_position - (168//2) + 64, y=323 + y_position)


    def draw_modifiers(self):
        # Batch modifier texture draws to reduce state changes
        modifiers_to_draw = ['mod_shinuchi']

        # Speed modifiers
        if global_data.modifiers.speed >= 4:
            modifiers_to_draw.append('mod_yonbai')
        elif global_data.modifiers.speed >= 3:
            modifiers_to_draw.append('mod_sanbai')
        elif global_data.modifiers.speed > 1:
            modifiers_to_draw.append('mod_baisaku')

        # Other modifiers
        if global_data.modifiers.display:
            modifiers_to_draw.append('mod_doron')
        if global_data.modifiers.inverse:
            modifiers_to_draw.append('mod_abekobe')
        if global_data.modifiers.random == 2:
            modifiers_to_draw.append('mod_detarame')
        elif global_data.modifiers.random == 1:
            modifiers_to_draw.append('mod_kimagure')

        # Draw all modifiers in one batch
        for modifier in modifiers_to_draw:
            tex.draw_texture('lane', modifier)

    def draw(self, game_screen: GameScreen):
        current_ms = game_screen.current_ms

        # Group 1: Background and lane elements
        tex.draw_texture('lane', 'lane_background')
        if self.branch_indicator is not None:
            self.branch_indicator.draw()
        self.gauge.draw()
        if self.lane_hit_effect is not None:
            self.lane_hit_effect.draw()
        tex.draw_texture('lane', 'lane_hit_circle')

        # Group 2: Judgement and hit effects
        if self.gogo_time is not None:
            self.gogo_time.draw()
        for anim in self.draw_judge_list:
            anim.draw()

        # Group 3: Notes and bars (game content)
        self.draw_bars(current_ms)
        self.draw_notes(current_ms, game_screen.start_ms)

        # Group 4: Lane covers and UI elements (batch similar textures)
        tex.draw_texture('lane', f'{self.player_number}p_lane_cover')
        tex.draw_texture('lane', 'drum')
        if global_data.modifiers.auto:
            tex.draw_texture('lane', 'auto_icon')

        # Group 5: Hit effects and animations
        for anim in self.draw_drum_hit_list:
            anim.draw()
        for anim in self.draw_arc_list:
            anim.draw(game_screen.mask_shader)
        for anim in self.gauge_hit_effect:
            anim.draw()

        # Group 6: UI overlays
        self.combo_display.draw()
        self.combo_announce.draw()
        tex.draw_texture('lane', 'lane_score_cover')
        tex.draw_texture('lane', f'{self.player_number}p_icon')
        tex.draw_texture('lane', 'lane_difficulty', frame=self.difficulty)

        # Group 7: Player-specific elements
        if not global_data.modifiers.auto:
            self.nameplate.draw(-62, 285)
        self.draw_modifiers()
        self.chara.draw()

        # Group 8: Special animations and counters
        if self.drumroll_counter is not None:
            self.drumroll_counter.draw()
        if self.balloon_anim is not None:
            self.balloon_anim.draw()
        if self.kusudama_anim is not None:
            self.kusudama_anim.draw()
        self.score_counter.draw()
        for anim in self.base_score_list:
            anim.draw()
        #ray.draw_circle(game_screen.width//2, game_screen.height, 300, ray.ORANGE)

    def draw_3d(self):
        pass

class Judgement:
    def __init__(self, type: str, big: bool, ms_display: Optional[float]=None):
        self.type = type
        self.big = big
        self.is_finished = False
        self.curr_hit_ms = None
        if ms_display is not None:
            self.curr_hit_ms = str(round(ms_display, 2))

        self.fade_animation_1 = Animation.create_fade(132, initial_opacity=0.5, delay=100)
        self.fade_animation_1.start()
        self.fade_animation_2 = Animation.create_fade(316 - 233.3, delay=233.3)
        self.fade_animation_2.start()
        self.move_animation = Animation.create_move(83, total_distance=15, start_position=144)
        self.move_animation.start()
        self.texture_animation = Animation.create_texture_change(100, textures=[(33, 50, 0), (50, 83, 1), (83, 100, 2), (100, float('inf'), 3)])
        self.texture_animation.start()

    def update(self, current_ms):
        animations = [self.fade_animation_1, self.fade_animation_2, self.move_animation, self.texture_animation]
        for anim in animations:
            anim.update(current_ms)

        if self.fade_animation_2.is_finished:
            self.is_finished = True

    def draw(self):
        y = self.move_animation.attribute
        index = self.texture_animation.attribute
        hit_fade = self.fade_animation_1.attribute
        fade = self.fade_animation_2.attribute
        if self.type == 'GOOD':
            if self.big:
                tex.draw_texture('hit_effect', 'hit_effect_good_big', fade=fade)
                tex.draw_texture('hit_effect', 'outer_good_big', frame=index, fade=hit_fade)
            else:
                tex.draw_texture('hit_effect', 'hit_effect_good', fade=fade)
                tex.draw_texture('hit_effect', 'outer_good', frame=index, fade=hit_fade)
            tex.draw_texture('hit_effect', 'judge_good', y=y, fade=fade)
        elif self.type == 'OK':
            if self.big:
                tex.draw_texture('hit_effect', 'hit_effect_ok_big', fade=fade)
                tex.draw_texture('hit_effect', 'outer_ok_big', frame=index, fade=hit_fade)
            else:
                tex.draw_texture('hit_effect', 'hit_effect_ok', fade=fade)
                tex.draw_texture('hit_effect', 'outer_ok', frame=index, fade=hit_fade)
            tex.draw_texture('hit_effect', 'judge_ok', y=y, fade=fade)
        elif self.type == 'BAD':
            tex.draw_texture('hit_effect', 'judge_bad', y=y, fade=fade)

class LaneHitEffect:
    def __init__(self, type: str):
        self.type = type
        self.fade = tex.get_animation(0, is_copy=True)
        self.fade.start()
        self.is_finished = False

    def update(self, current_ms: float):
        self.fade.update(current_ms)
        if self.fade.is_finished:
            self.is_finished = True

    def draw(self):
        if self.type == 'GOOD':
            tex.draw_texture('lane', 'lane_hit_effect', frame=2, fade=self.fade.attribute)
        elif self.type == 'DON':
            tex.draw_texture('lane', 'lane_hit_effect', frame=0, fade=self.fade.attribute)
        elif self.type == 'KAT':
            tex.draw_texture('lane', 'lane_hit_effect', frame=1, fade=self.fade.attribute)

class DrumHitEffect:
    def __init__(self, type: str, side: str):
        self.type = type
        self.side = side
        self.is_finished = False
        self.fade = tex.get_animation(1, is_copy=True)
        self.fade.start()

    def update(self, current_ms: float):
        self.fade.update(current_ms)
        if self.fade.is_finished:
            self.is_finished = True

    def draw(self):
        if self.type == 'DON':
            if self.side == 'L':
                tex.draw_texture('lane', 'drum_don_l', fade=self.fade.attribute)
            elif self.side == 'R':
                tex.draw_texture('lane', 'drum_don_r', fade=self.fade.attribute)
        elif self.type == 'KAT':
            if self.side == 'L':
                tex.draw_texture('lane', 'drum_kat_l', fade=self.fade.attribute)
            elif self.side == 'R':
                tex.draw_texture('lane', 'drum_kat_r', fade=self.fade.attribute)

class GaugeHitEffect:
    # Pre-define color thresholds for better performance
    _COLOR_THRESHOLDS = [(0.70, ray.WHITE), (0.80, ray.YELLOW), (0.90, ray.ORANGE), (1.00, ray.RED)]

    def __init__(self, note_type: int, big: bool):
        self.note_type = note_type
        self.is_big = big
        self.texture_change = tex.get_animation(2, is_copy=True)
        self.texture_change.start()
        self.circle_fadein = Animation.create_fade(133, initial_opacity=0.0, final_opacity=1.0, delay=16.67)
        self.circle_fadein.start()
        self.resize = Animation.create_texture_resize(233, delay=self.texture_change.duration, initial_size=0.75, final_size=1.15)
        self.resize.start()
        self.fade_out = Animation.create_fade(66, delay=233)
        self.fade_out.start()
        self.rotation = Animation.create_fade(300, delay=116.67, initial_opacity=0.0, final_opacity=1.0)
        self.rotation.start()
        self.color = ray.fade(ray.YELLOW, self.circle_fadein.attribute)
        self.is_finished = False

        self.texture_color = ray.WHITE
        self.dest_width = 152
        self.dest_height = 152
        self.origin = ray.Vector2(76, 76)  # 152/2
        self.rotation_angle = 0
        self.x2_pos = -152
        self.y2_pos = -152

        # Cache for texture selection
        self.circle_texture = 'hit_effect_circle_big' if self.is_big else 'hit_effect_circle'
        self._last_resize_value = -1
        self._cached_texture_color = ray.WHITE

    def _get_texture_color_for_resize(self, resize_value):
        """Calculate texture color based on resize attribute value with caching"""
        # Use cached value if resize hasn't changed significantly
        if abs(resize_value - self._last_resize_value) < 0.01:
            return self._cached_texture_color

        self._last_resize_value = resize_value

        if resize_value >= 1.00:
            self._cached_texture_color = ray.RED
        else:
            # Use pre-defined thresholds for faster lookup
            self._cached_texture_color = ray.WHITE
            for threshold, color in self._COLOR_THRESHOLDS:
                if resize_value <= threshold:
                    self._cached_texture_color = color
                    break

        return self._cached_texture_color

    def update(self, current_ms):
        # Update all animations
        self.texture_change.update(current_ms)
        self.circle_fadein.update(current_ms)
        self.fade_out.update(current_ms)
        self.resize.update(current_ms)
        self.rotation.update(current_ms)

        # Update circle color with optimized calculation
        base_color = ray.WHITE if self.circle_fadein.is_finished else ray.YELLOW
        fade_value = min(self.fade_out.attribute, self.circle_fadein.attribute)
        self.color = ray.fade(base_color, fade_value)

        # Pre-compute drawing values only when resize changes significantly
        resize_val = self.resize.attribute
        if abs(resize_val - getattr(self, '_last_resize_calc', -1)) > 0.005:
            self._last_resize_calc = resize_val
            self.texture_color = self._get_texture_color_for_resize(resize_val)
            self.dest_width = 152 * resize_val
            self.dest_height = 152 * resize_val
            self.origin = ray.Vector2(self.dest_width / 2, self.dest_height / 2)
            self.x2_pos = -152 + (152 * resize_val)
            self.y2_pos = -152 + (152 * resize_val)

        self.rotation_angle = self.rotation.attribute * 100

        # Check if finished
        if self.fade_out.is_finished:
            self.is_finished = True

    def draw(self):
        fade_value = self.fade_out.attribute

        # Main hit effect texture
        tex.draw_texture('gauge', 'hit_effect',
                        frame=self.texture_change.attribute,
                        x2=self.x2_pos,
                        y2=self.y2_pos,
                        color=ray.fade(self.texture_color, fade_value),
                        origin=self.origin,
                        rotation=self.rotation_angle,
                        center=True)

        # Note type texture
        tex.draw_texture('notes', str(self.note_type),
                        x=1158, y=101,
                        fade=fade_value)

        # Circle effect texture (use cached texture name)
        tex.draw_texture('gauge', self.circle_texture, color=self.color)

class NoteArc:
    def __init__(self, note_type: int, current_ms: float, player_number: int, big: bool, is_balloon: bool):
        self.note_type = note_type
        self.is_big = big
        self.is_balloon = is_balloon
        self.arc_points = 100
        self.arc_duration = 22
        self.current_progress = 0
        self.create_ms = current_ms
        self.player_number = player_number

        self.explosion_point_index = 0
        self.points_per_explosion = 5

        curve_height = 425
        self.start_x, self.start_y = 350, 192
        self.end_x, self.end_y = 1158, 101
        self.explosion_x = self.start_x
        self.explosion_y = self.start_y

        if self.player_number == 1:
            # Control point influences the curve shape
            self.control_x = (self.start_x + self.end_x) // 2
            self.control_y = min(self.start_y, self.end_y) - curve_height  # Arc upward
        else:
            self.control_x = (self.start_x + self.end_x) // 2
            self.control_y = max(self.start_y, self.end_y) + curve_height  # Arc downward

        self.x_i = self.start_x
        self.y_i = self.start_y
        self.is_finished = False
        self.arc_points_cache = []
        for i in range(self.arc_points + 1):
            t = i / self.arc_points
            t_inv = 1.0 - t
            x = int(t_inv * t_inv * self.start_x + 2 * t_inv * t * self.control_x + t * t * self.end_x)
            y = int(t_inv * t_inv * self.start_y + 2 * t_inv * t * self.control_y + t * t * self.end_y)
            self.arc_points_cache.append((x, y))

        self.explosion_x, self.explosion_y = self.arc_points_cache[0]
        self.explosion_anim = tex.get_animation(22)
        self.explosion_anim.start()

    def update(self, current_ms: float):
        ms_since_call = (current_ms - self.create_ms) / 16.67
        ms_since_call = max(0, min(ms_since_call, self.arc_duration))

        self.current_progress = ms_since_call / self.arc_duration
        if self.current_progress >= 1.0:
            self.is_finished = True
            self.x_i, self.y_i = self.arc_points_cache[-1]
            return

        point_index = int(self.current_progress * self.arc_points)
        if point_index < len(self.arc_points_cache):
            self.x_i, self.y_i = self.arc_points_cache[point_index]
        else:
            self.x_i, self.y_i = self.arc_points_cache[-1]

        self.explosion_anim.update(current_ms)
        if self.explosion_anim.is_finished:
            self.explosion_point_index = min(
                self.explosion_point_index + self.points_per_explosion,
                len(self.arc_points_cache) - 1
            )

            self.explosion_x, self.explosion_y = self.arc_points_cache[self.explosion_point_index*4]
            self.explosion_anim.restart()

    def draw(self, mask_shader: ray.Shader):
        if self.is_balloon:
            rainbow = tex.textures['balloon']['rainbow']
            trail_length_ratio = 0.5
            trail_start_progress = max(0, self.current_progress - trail_length_ratio)
            trail_end_progress = self.current_progress

            if trail_end_progress > trail_start_progress:
                crop_start_x = int(trail_start_progress * rainbow.width)
                crop_end_x = int(trail_end_progress * rainbow.width)
                crop_width = crop_end_x - crop_start_x

                if crop_width > 0:
                    src = ray.Rectangle(crop_start_x, 0, crop_width, rainbow.height)
                    ray.begin_shader_mode(mask_shader)
                    tex.draw_texture('balloon', 'rainbow_mask', src=src, x=crop_start_x, x2=-rainbow.width + crop_width)
                    ray.end_shader_mode()

                    tex.draw_texture('balloon', 'explosion', x=self.explosion_x, y=self.explosion_y-30, frame=self.explosion_anim.attribute)
        '''
        elif self.is_big:
            tex.draw_texture('hit_effect', 'explosion', x=self.explosion_x, y=self.explosion_y-30, frame=self.explosion_anim.attribute)
        '''
        tex.draw_texture('notes', str(self.note_type), x=self.x_i, y=self.y_i)

class DrumrollCounter:
    def __init__(self, current_ms: float):
        self.create_ms = current_ms
        self.is_finished = False
        self.total_duration = 1349
        self.drumroll_count = 0
        self.fade_animation = tex.get_animation(8)
        self.fade_animation.start()
        self.stretch_animation = tex.get_animation(9)

    def update_count(self, count: int, elapsed_time: float):
        self.total_duration = elapsed_time + 1349
        self.fade_animation.delay = self.total_duration - 166
        if self.drumroll_count != count:
            self.drumroll_count = count
            self.stretch_animation.start()

    def update(self, current_ms: float, drumroll_count: int):
        self.stretch_animation.update(current_ms)
        self.fade_animation.update(current_ms)

        elapsed_time = current_ms - self.create_ms
        if drumroll_count != 0:
            self.update_count(drumroll_count, elapsed_time)
        if self.fade_animation.is_finished:
            self.is_finished = True

    def draw(self):
        color = ray.fade(ray.WHITE, self.fade_animation.attribute)
        tex.draw_texture('drumroll_counter', 'bubble', color=color)
        counter = str(self.drumroll_count)
        total_width = len(counter) * 52
        for i, digit in enumerate(counter):
            tex.draw_texture('drumroll_counter', 'counter', color=color, frame=int(digit), x=-(total_width//2)+(i*52), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)

class BalloonAnimation:
    def __init__(self, current_ms: float, balloon_total: int):
        self.create_ms = current_ms
        self.is_finished = False
        self.total_duration = 83.33
        self.color = ray.fade(ray.WHITE, 1.0)
        self.balloon_count = 0
        self.balloon_total = balloon_total
        self.is_popped = False
        self.stretch_animation = tex.get_animation(6)
        self.fade_animation = tex.get_animation(7)
        self.fade_animation.start()

    def update_count(self, balloon_count: int):
        if self.balloon_count != balloon_count:
            self.balloon_count = balloon_count
            self.stretch_animation.start()

    def update(self, current_ms: float, balloon_count: int, is_popped: bool):
        self.update_count(balloon_count)
        self.stretch_animation.update(current_ms)
        self.is_popped = is_popped

        elapsed_time = current_ms - self.create_ms
        if self.is_popped:
            self.fade_animation.update(current_ms)
            self.color = ray.fade(ray.WHITE, self.fade_animation.attribute)
        else:
            self.total_duration = elapsed_time + 166
            self.fade_animation.delay = self.total_duration - 166
        if self.fade_animation.is_finished:
            self.is_finished = True

    def draw(self):
        if self.is_popped:
            tex.draw_texture('balloon', 'pop', frame=7, color=self.color)
        elif self.balloon_count >= 1:
            balloon_index = min(6, (self.balloon_count - 1) * 6 // self.balloon_total)
            tex.draw_texture('balloon', 'pop', frame=balloon_index, color=self.color, index=global_data.player_num-1)
        if self.balloon_count > 0:
            tex.draw_texture('balloon', 'bubble')
            counter = str(max(0, self.balloon_total - self.balloon_count + 1))
            total_width = len(counter) * 52
            for i, digit in enumerate(counter):
                tex.draw_texture('balloon', 'counter', frame=int(digit), color=self.color, x=-(total_width // 2) + (i * 52), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)

class KusudamaAnimation:
    def __init__(self, balloon_total: int):
        self.balloon_total = balloon_total
        self.move_down = tex.get_animation(11)
        self.move_up = tex.get_animation(12)
        self.renda_move_up = tex.get_animation(13)
        self.renda_move_down = tex.get_animation(18)
        self.renda_fade_in = tex.get_animation(14)
        self.renda_fade_out = tex.get_animation(20)
        self.stretch_animation = tex.get_animation(15)
        self.breathing = tex.get_animation(16)
        self.renda_breathe = tex.get_animation(17)
        self.open = tex.get_animation(19)
        self.fade_out = tex.get_animation(21)
        self.balloon_count = 0
        self.is_popped = False
        self.is_finished = False
        self.move_down.start()
        self.move_up.start()
        self.renda_move_up.start()
        self.renda_move_down.start()
        self.renda_fade_in.start()

        self.open.reset()
        self.renda_fade_out.reset()
        self.fade_out.reset()

    def update_count(self, balloon_count: int):
        if self.balloon_count != balloon_count:
            self.balloon_count = balloon_count
            self.stretch_animation.start()
            self.breathing.start()

    def update(self, current_ms, is_popped: bool):
        if is_popped and not self.is_popped:
            self.is_popped = True
            self.open.start()
            self.renda_fade_out.start()
            self.fade_out.start()
        self.move_down.update(current_ms)
        self.move_up.update(current_ms)
        self.renda_move_up.update(current_ms)
        self.renda_move_down.update(current_ms)
        self.renda_fade_in.update(current_ms)
        self.renda_fade_out.update(current_ms)
        self.fade_out.update(current_ms)
        self.stretch_animation.update(current_ms)
        self.breathing.update(current_ms)
        self.renda_breathe.update(current_ms)
        self.open.update(current_ms)
        self.is_finished = self.fade_out.is_finished
    def draw(self):
        y = self.move_down.attribute - self.move_up.attribute
        renda_y = -self.renda_move_up.attribute + self.renda_move_down.attribute + self.renda_breathe.attribute
        tex.draw_texture('kusudama', 'kusudama', frame=self.open.attribute, y=y, scale=self.breathing.attribute, center=True, fade=self.fade_out.attribute)
        tex.draw_texture('kusudama', 'renda', y=renda_y, fade=min(self.renda_fade_in.attribute, self.renda_fade_out.attribute))

        if self.move_up.is_finished and not self.is_popped:
            counter = str(max(0, self.balloon_total - self.balloon_count))
            if counter == '0':
                return
            total_width = len(counter) * 150
            for i, digit in enumerate(counter):
                tex.draw_texture('kusudama', 'counter', frame=int(digit), x=-(total_width // 2) + (i * 150), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)

class Combo:
    def __init__(self, combo: int, current_ms: float):
        self.combo = combo
        self.stretch_animation = tex.get_animation(5)
        self.color = [ray.fade(ray.WHITE, 1), ray.fade(ray.WHITE, 1), ray.fade(ray.WHITE, 1)]
        self.glimmer_dict = {0: 0, 1: 0, 2: 0}
        self.total_time = 250
        self.cycle_time = self.total_time * 2
        self.start_times = [
                    current_ms,
                    current_ms + (2 / 3) * self.cycle_time,
                    current_ms + (4 / 3) * self.cycle_time
                ]

    def update_count(self, combo: int):
        if self.combo != combo:
            self.combo = combo
            self.stretch_animation.start()

    def update(self, current_ms: float, combo: int):
        self.update_count(combo)
        self.stretch_animation.update(current_ms)

        for i in range(3):
            elapsed_time = current_ms - self.start_times[i]
            if elapsed_time > self.cycle_time:
                cycles_completed = elapsed_time // self.cycle_time
                self.start_times[i] += cycles_completed * self.cycle_time
                elapsed_time = current_ms - self.start_times[i]
            if elapsed_time <= self.total_time:
                self.glimmer_dict[i] = -int(elapsed_time // 16.67)
                fade_start_time = self.total_time - 164
                if elapsed_time >= fade_start_time:
                    fade = 1 - (elapsed_time - fade_start_time) / 164
                else:
                    fade = 1
            else:
                self.glimmer_dict[i] = 0
                fade = 0
            self.color[i] = ray.fade(ray.WHITE, fade)

    def draw(self):
        if self.combo < 3:
            return

        # Cache string conversion
        if self.combo != getattr(self, '_cached_combo_value', -1):
            self._cached_combo_value = self.combo
            self._cached_combo_str = str(self.combo)
        counter = self._cached_combo_str

        if self.combo < 100:
            margin = 30
            total_width = len(counter) * margin
            tex.draw_texture('combo', 'combo')
            for i, digit in enumerate(counter):
                tex.draw_texture('combo', 'counter', frame=int(digit), x=-(total_width // 2) + (i * margin), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)
        else:
            margin = 35
            total_width = len(counter) * margin
            tex.draw_texture('combo', 'combo_100')
            for i, digit in enumerate(counter):
                tex.draw_texture('combo', 'counter_100', frame=int(digit), x=-(total_width // 2) + (i * margin), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)
            glimmer_positions = [(225, 210), (200, 230), (250, 230)]
            for j, (x, y) in enumerate(glimmer_positions):
                for i in range(3):
                    tex.draw_texture('combo', 'gleam', x=x+(i*30), y=y+self.glimmer_dict[j], color=self.color[j])

class ScoreCounter:
    def __init__(self, score: int):
        self.score = score
        self.stretch = tex.get_animation(4)

    def update_count(self, score: int):
        if self.score != score:
            self.score = score
            self.stretch.start()

    def update(self, current_ms: float, score: int):
        self.update_count(score)
        if self.score > 0:
            self.stretch.update(current_ms)

    def draw(self):
        # Cache string conversion
        if self.score != getattr(self, '_cached_score_value', -1):
            self._cached_score_value = self.score
            self._cached_score_str = str(self.score)
        counter = self._cached_score_str

        x, y = 150, 185
        margin = 20
        total_width = len(counter) * margin
        start_x = x - total_width
        for i, digit in enumerate(counter):
            tex.draw_texture('lane', 'score_number', frame=int(digit), x=start_x + (i * margin), y=y - self.stretch.attribute, y2=self.stretch.attribute)

class ScoreCounterAnimation:
    def __init__(self, player_num: str, counter: int):
        self.counter = counter
        self.fade_animation_1 = Animation.create_fade(50, initial_opacity=0.0, final_opacity=1.0)
        self.fade_animation_1.start()
        self.move_animation_1 = Animation.create_move(80, total_distance=-20, start_position=175)
        self.move_animation_1.start()
        self.fade_animation_2 = Animation.create_fade(80, delay=366.74)
        self.fade_animation_2.start()
        self.move_animation_2 = Animation.create_move(66, total_distance=5, start_position=145, delay=80)
        self.move_animation_2.start()
        self.move_animation_3 = Animation.create_move(66, delay=279.36, total_distance=-2, start_position=146)
        self.move_animation_3.start()
        self.move_animation_4 = Animation.create_move(80, delay=366.74, total_distance=10, start_position=148)
        self.move_animation_4.start()

        if player_num == '2':
            self.base_color = ray.Color(84, 250, 238, 255)
        else:
            self.base_color = ray.Color(254, 102, 0, 255)
        self.color = ray.fade(self.base_color, 1.0)
        self.is_finished = False

        # Cache string and layout calculations
        self.counter_str = str(counter)
        self.margin = 20
        self.total_width = len(self.counter_str) * self.margin
        self.y_pos_list = []

    def update(self, current_ms: float):
        self.fade_animation_1.update(current_ms)
        self.move_animation_1.update(current_ms)
        self.move_animation_2.update(current_ms)
        self.move_animation_3.update(current_ms)
        self.move_animation_4.update(current_ms)
        self.fade_animation_2.update(current_ms)

        fade_value = self.fade_animation_2.attribute if self.fade_animation_1.is_finished else self.fade_animation_1.attribute
        self.color = ray.fade(self.base_color, fade_value)

        if self.fade_animation_2.is_finished:
            self.is_finished = True

        # Cache y positions
        self.y_pos_list = [self.move_animation_4.attribute + i*5 for i in range(1, len(self.counter_str)+1)]

    def draw(self):
        x = self.move_animation_2.attribute if self.move_animation_1.is_finished else self.move_animation_1.attribute
        if x == 0:
            return

        start_x = x - self.total_width

        for i, digit in enumerate(self.counter_str):
            if self.move_animation_3.is_finished:
                y = self.y_pos_list[i]
            elif self.move_animation_2.is_finished:
                y = self.move_animation_3.attribute
            else:
                y = 148
            tex.draw_texture('lane', 'score_number',
                           frame=int(digit),
                           x=start_x + (i * self.margin),
                           y=y,
                           color=self.color)

class SongInfo:
    def __init__(self, song_name: str, genre: int):
        self.song_name = song_name
        self.genre = genre
        self.song_title = OutlinedText(song_name, 40, ray.WHITE, ray.BLACK, outline_thickness=5)
        self.fade = tex.get_animation(3)

    def update(self, current_ms: float):
        self.fade.update(current_ms)

    def draw(self):
        tex.draw_texture('song_info', 'song_num', fade=self.fade.attribute, frame=global_data.songs_played % 4)

        text_x = 1252 - self.song_title.texture.width
        text_y = 50 - self.song_title.texture.height//2
        dest = ray.Rectangle(text_x, text_y, self.song_title.texture.width, self.song_title.texture.height)
        self.song_title.draw(self.song_title.default_src, dest, ray.Vector2(0, 0), 0, ray.fade(ray.WHITE, 1 - self.fade.attribute))

        if self.genre < 9:
            tex.draw_texture('song_info', 'genre', fade=1 - self.fade.attribute, frame=self.genre)

class ResultTransition:
    def __init__(self, player_num: int):
        self.player_num = player_num
        self.move = global_tex.get_animation(5)
        self.move.reset()
        self.is_finished = False
        self.is_started = False

    def start(self):
        self.move.start()

    def update(self, current_ms: float):
        self.move.update(current_ms)
        self.is_started = self.move.is_started
        self.is_finished = self.move.is_finished

    def draw(self):
        x = 0
        screen_width = 1280
        while x < screen_width:
            global_tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter', frame=0, x=x, y=-720 + self.move.attribute)
            global_tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter', frame=0, x=x, y=720 - self.move.attribute)
            global_tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter_footer', x=x, y=-432 + self.move.attribute)
            global_tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter_footer', x=x, y=1008 - self.move.attribute)
            x += 256

class GogoTime:
    def __init__(self):
        self.explosion_anim = tex.get_animation(23)
        self.fire_resize = tex.get_animation(24)
        self.fire_change = tex.get_animation(25)

        self.explosion_anim.start()
        self.fire_resize.start()
        self.fire_change.start()
    def update(self, current_time_ms: float):
        self.explosion_anim.update(current_time_ms)
        self.fire_resize.update(current_time_ms)
        self.fire_change.update(current_time_ms)

    def draw(self):
        tex.draw_texture('gogo_time', 'fire', scale=self.fire_resize.attribute, frame=self.fire_change.attribute, fade=0.5, center=True)
        if not self.explosion_anim.is_finished:
            for i in range(5):
                tex.draw_texture('gogo_time', 'explosion', frame=self.explosion_anim.attribute, index=i)

class ComboAnnounce:
    def __init__(self, combo: int, current_time_ms: float):
        self.combo = combo
        self.wait = current_time_ms
        self.fade = Animation.create_fade(100)
        self.fade.start()
        self.is_finished = False

    def update(self, current_time_ms: float):
        if current_time_ms >= self.wait + 1666.67 and not self.is_finished:
            self.fade.start()
            self.is_finished = True

        self.fade.update(current_time_ms)

    def draw(self):
        if self.combo == 0:
            return
        if not self.is_finished:
            fade = 1 - self.fade.attribute
        else:
            fade = self.fade.attribute
        tex.draw_texture('combo', f'announce_bg_{global_data.player_num}p', fade=fade)

        if self.combo >= 1000:
            thousands = self.combo // 1000
            remaining_hundreds = (self.combo % 1000) // 100
            thousands_offset = -110
            hundreds_offset = 20
            if self.combo % 1000 == 0:
                tex.draw_texture('combo', 'announce_number', frame=thousands-1, x=-23, fade=fade)
                tex.draw_texture('combo', 'announce_add', frame=0, x=435, fade=fade)
            else:
                if thousands <= 5:
                    tex.draw_texture('combo', 'announce_add', frame=thousands, x=429 + thousands_offset, fade=fade)
                if remaining_hundreds > 0:
                    tex.draw_texture('combo', 'announce_number', frame=remaining_hundreds-1, x=hundreds_offset, fade=fade)
            text_offset = -30
        else:
            text_offset = 0
            tex.draw_texture('combo', 'announce_number', frame=self.combo // 100 - 1, x=0, fade=fade)
        tex.draw_texture('combo', 'announce_text', x=-text_offset/2, fade=fade)

class BranchIndicator:
    def __init__(self):
        self.difficulty = 'normal'
        self.diff_2 = self.difficulty
        self.diff_down = Animation.create_move(100, total_distance=20, ease_out='quadratic')
        self.diff_up = Animation.create_move(133, total_distance=70, delay=self.diff_down.duration, ease_out='quadratic')
        self.diff_fade = Animation.create_fade(133, delay=self.diff_down.duration)
        self.level_fade = Animation.create_fade(116, initial_opacity=0.0, final_opacity=1.0, reverse_delay=116*10)
        self.level_scale = Animation.create_texture_resize(116, initial_size=1.0, final_size=1.2, reverse_delay=0)
        self.direction = 1
    def update(self, current_time_ms):
        self.diff_down.update(current_time_ms)
        self.diff_up.update(current_time_ms)
        self.diff_fade.update(current_time_ms)
        self.level_fade.update(current_time_ms)
        self.level_scale.update(current_time_ms)
    def level_up(self, difficulty):
        self.diff_2 = self.difficulty
        self.difficulty = difficulty
        self.diff_down.start()
        self.diff_up.start()
        self.diff_fade.start()
        self.level_fade.start()
        self.level_scale.start()
        self.direction = 1
    def level_down(self, difficulty):
        self.diff_2 = self.difficulty
        self.difficulty = difficulty
        self.diff_down.start()
        self.diff_up.start()
        self.diff_fade.start()
        self.level_fade.start()
        self.level_scale.start()
        self.direction = -1
    def draw(self):
        if self.difficulty == 'expert':
            tex.draw_texture('branch', 'expert_bg', fade=min(0.5, 1 - self.diff_fade.attribute))
        if self.difficulty == 'master':
            tex.draw_texture('branch', 'master_bg', fade=min(0.5, 1 - self.diff_fade.attribute))
        if self.direction == -1:
            tex.draw_texture('branch', 'level_down', scale=self.level_scale.attribute, fade=self.level_fade.attribute, center=True)
        else:
            tex.draw_texture('branch', 'level_up', scale=self.level_scale.attribute, fade=self.level_fade.attribute, center=True)
        tex.draw_texture('branch', self.diff_2, y=(self.diff_down.attribute - self.diff_up.attribute) * self.direction, fade=self.diff_fade.attribute)
        tex.draw_texture('branch', self.difficulty, y=(self.diff_up.attribute * (self.direction*-1)) - (70*self.direction*-1), fade=1 - self.diff_fade.attribute)

class Gauge:
    def __init__(self, player_num: str, difficulty: int, level: int, total_notes: int):
        self.player_num = player_num
        self.string_diff = "_hard"
        self.gauge_length = 0
        self.previous_length = 0
        self.total_notes = total_notes
        self.difficulty = min(3, difficulty)
        self.clear_start = [52, 60, 69, 69]
        self.gauge_max = 87
        self.level = min(10, level)
        if self.difficulty == 2:
            self.string_diff = "_hard"
        elif self.difficulty == 1:
            self.string_diff = "_normal"
        elif self.difficulty == 0:
            self.string_diff = "_easy"
        self.is_clear = False
        self.is_rainbow = False
        self.table = [
            [
                None,
                {"clear_rate": 36.0, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
                {"clear_rate": 38.0, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
                {"clear_rate": 38.0, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
                {"clear_rate": 44.0, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
                {"clear_rate": 44.0, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
            ],
            [
                None,
                {"clear_rate": 45.939, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
                {"clear_rate": 45.939, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
                {"clear_rate": 48.676, "ok_multiplier": 0.75, "bad_multiplier": -0.5},
                {"clear_rate": 49.232, "ok_multiplier": 0.75, "bad_multiplier": -0.75},
                {"clear_rate": 52.5, "ok_multiplier": 0.75, "bad_multiplier": -1.0},
                {"clear_rate": 52.5, "ok_multiplier": 0.75, "bad_multiplier": -1.0},
                {"clear_rate": 52.5, "ok_multiplier": 0.75, "bad_multiplier": -1.0},
            ],
            [
                None,
                {"clear_rate": 54.325, "ok_multiplier": 0.75, "bad_multiplier": -0.75},
                {"clear_rate": 54.325, "ok_multiplier": 0.75, "bad_multiplier": -0.75},
                {"clear_rate": 50.774, "ok_multiplier": 0.75, "bad_multiplier": -1.0},
                {"clear_rate": 48.410, "ok_multiplier": 0.75, "bad_multiplier": -1.17},
                {"clear_rate": 47.246, "ok_multiplier": 0.75, "bad_multiplier": -1.25},
                {"clear_rate": 48.120, "ok_multiplier": 0.75, "bad_multiplier": -1.25},
                {"clear_rate": 48.120, "ok_multiplier": 0.75, "bad_multiplier": -1.25},
                {"clear_rate": 48.120, "ok_multiplier": 0.75, "bad_multiplier": -1.25},
            ],
            [
                None,
                {"clear_rate": 56.603, "ok_multiplier": 0.5, "bad_multiplier": -1.6},
                {"clear_rate": 56.603, "ok_multiplier": 0.5, "bad_multiplier": -1.6},
                {"clear_rate": 56.603, "ok_multiplier": 0.5, "bad_multiplier": -1.6},
                {"clear_rate": 56.603, "ok_multiplier": 0.5, "bad_multiplier": -1.6},
                {"clear_rate": 56.603, "ok_multiplier": 0.5, "bad_multiplier": -1.6},
                {"clear_rate": 56.603, "ok_multiplier": 0.5, "bad_multiplier": -1.6},
                {"clear_rate": 56.603, "ok_multiplier": 0.5, "bad_multiplier": -1.6},
                {"clear_rate": 56.0, "ok_multiplier": 0.5, "bad_multiplier": -2.0},
                {"clear_rate": 61.428, "ok_multiplier": 0.5, "bad_multiplier": -2.0},
                {"clear_rate": 61.428, "ok_multiplier": 0.5, "bad_multiplier": -2.0},
            ]
        ]
        self.gauge_update_anim = tex.get_animation(10)
        self.rainbow_fade_in = None
        self.rainbow_animation = None

    def add_good(self):
        self.gauge_update_anim.start()
        self.previous_length = int(self.gauge_length)
        self.gauge_length += (1 / self.total_notes) * (100 * (self.clear_start[self.difficulty] / self.table[self.difficulty][self.level]["clear_rate"]))
        if self.gauge_length > self.gauge_max:
            self.gauge_length = self.gauge_max

    def add_ok(self):
        self.gauge_update_anim.start()
        self.previous_length = int(self.gauge_length)
        self.gauge_length += ((1 * self.table[self.difficulty][self.level]["ok_multiplier"]) / self.total_notes) * (100 * (self.clear_start[self.difficulty] / self.table[self.difficulty][self.level]["clear_rate"]))
        if self.gauge_length > self.gauge_max:
            self.gauge_length = self.gauge_max

    def add_bad(self):
        self.previous_length = int(self.gauge_length)
        self.gauge_length += ((1 * self.table[self.difficulty][self.level]["bad_multiplier"]) / self.total_notes) * (100 * (self.clear_start[self.difficulty] / self.table[self.difficulty][self.level]["clear_rate"]))
        if self.gauge_length < 0:
            self.gauge_length = 0

    def update(self, current_ms: float):
        self.is_clear = self.gauge_length > self.clear_start[min(self.difficulty, 2)]
        self.is_rainbow = self.gauge_length == self.gauge_max
        if self.gauge_length == self.gauge_max and self.rainbow_fade_in is None:
            self.rainbow_fade_in = Animation.create_fade(450, initial_opacity=0.0, final_opacity=1.0)
            self.rainbow_fade_in.start()
        self.gauge_update_anim.update(current_ms)

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
        tex.draw_texture('gauge', 'border' + self.string_diff)
        tex.draw_texture('gauge', f'{self.player_num}p_unfilled' + self.string_diff)
        gauge_length = int(self.gauge_length)
        clear_point = self.clear_start[self.difficulty]

        # Batch draw gauge bars by type instead of individual draws
        if gauge_length > 0:
            # Draw pre-clear bars as a batch
            pre_clear_length = min(gauge_length, clear_point - 1)
            if pre_clear_length > 0:
                for i in range(pre_clear_length):
                    tex.draw_texture('gauge', f'{self.player_num}p_bar', x=i*8)

            # Draw clear transition bar if applicable
            if gauge_length >= clear_point - 1:
                tex.draw_texture('gauge', 'bar_clear_transition', x=(clear_point - 1)*8)

            # Draw post-clear bars as a batch
            if gauge_length > clear_point:
                post_clear_start = clear_point
                post_clear_length = gauge_length - post_clear_start
                for i in range(post_clear_length):
                    x_pos = (post_clear_start + i) * 8
                    tex.draw_texture('gauge', 'bar_clear_top', x=x_pos)
                    tex.draw_texture('gauge', 'bar_clear_bottom', x=x_pos)

        # Rainbow effect for full gauge
        if gauge_length == self.gauge_max and self.rainbow_fade_in is not None and self.rainbow_animation is not None:
            if 0 < self.rainbow_animation.attribute < 8:
                tex.draw_texture('gauge', 'rainbow' + self.string_diff, frame=self.rainbow_animation.attribute-1, fade=self.rainbow_fade_in.attribute)
            tex.draw_texture('gauge', 'rainbow' + self.string_diff, frame=self.rainbow_animation.attribute, fade=self.rainbow_fade_in.attribute)
        if self.gauge_update_anim is not None and gauge_length <= self.gauge_max and gauge_length > self.previous_length:
            if gauge_length == self.clear_start[self.difficulty]:
                tex.draw_texture('gauge', 'bar_clear_transition_fade', x=gauge_length*8, fade=self.gauge_update_anim.attribute)
            elif gauge_length > self.clear_start[self.difficulty]:
                tex.draw_texture('gauge', 'bar_clear_fade', x=gauge_length*8, fade=self.gauge_update_anim.attribute)
            else:
                tex.draw_texture('gauge', f'{self.player_num}p_bar_fade', x=gauge_length*8, fade=self.gauge_update_anim.attribute)
        tex.draw_texture('gauge', 'overlay' + self.string_diff, fade=0.15)

        # Draw clear status indicators
        if gauge_length >= clear_point:
            tex.draw_texture('gauge', 'clear', index=min(2, self.difficulty))
            tex.draw_texture('gauge', 'tamashii')
        else:
            tex.draw_texture('gauge', 'clear_dark', index=min(2, self.difficulty))
            tex.draw_texture('gauge', 'tamashii_dark')
