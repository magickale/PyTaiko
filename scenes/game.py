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
from libs.global_objects import Nameplate
from libs.texture import tex
from libs.tja import (
    Balloon,
    Drumroll,
    Note,
    TJAParser,
    apply_modifiers,
    calculate_base_score,
)
from libs.transition import Transition
from libs.utils import (
    OutlinedText,
    get_current_ms,
    global_data,
    is_l_don_pressed,
    is_l_kat_pressed,
    is_r_don_pressed,
    is_r_kat_pressed,
    session_data,
)
from libs.video import VideoPlayer


class GameScreen:
    JUDGE_X = 414
    def __init__(self):
        self.width = 1280
        self.current_ms = 0
        self.screen_init = False
        self.end_ms = 0
        self.start_delay = 1000
        self.song_started = False

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
            self.tja = TJAParser(song, start_delay=self.start_delay, distance=self.width - GameScreen.JUDGE_X)
            if self.tja.metadata.bgmovie != Path() and self.tja.metadata.bgmovie.exists():
                self.movie = VideoPlayer(self.tja.metadata.bgmovie)
                self.movie.set_volume(0.0)
            else:
                self.movie = None
            session_data.song_title = self.tja.metadata.title.get(global_data.config['general']['language'].lower(), self.tja.metadata.title['en'])
            if self.tja.metadata.wave.exists() and self.tja.metadata.wave.is_file():
                self.song_music = audio.load_sound(self.tja.metadata.wave)
                audio.normalize_sound(self.song_music, 0.1935)

        self.player_1 = Player(self, global_data.player_num, difficulty)
        if self.tja is not None:
            self.start_ms = (get_current_ms() - self.tja.metadata.offset*1000)

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True
            self.movie = None
            self.song_music = None
            tex.load_screen_textures('game')
            self.background = Background(global_data.player_num)
            self.load_sounds()
            self.init_tja(global_data.selected_song, session_data.selected_difficulty)
            self.song_info = SongInfo(session_data.song_title, 'TEST')
            self.result_transition = ResultTransition(global_data.player_num)
            if self.tja is not None:
                subtitle = self.tja.metadata.subtitle.get(global_data.config['general']['language'].lower(), '')
            else:
                subtitle = ''
            self.transition = Transition(session_data.song_title, subtitle, is_second=True)
            self.transition.start()

    def on_screen_end(self, next_screen):
        self.screen_init = False
        tex.unload_textures()
        if self.song_music is not None:
            audio.unload_sound(self.song_music)
        self.song_started = False
        self.end_ms = 0
        self.movie = None
        self.background.unload()
        return next_screen

    def write_score(self):
        if self.tja is None:
            return
        if global_data.modifiers.auto:
            return
        with sqlite3.connect('scores.db') as con:
            cursor = con.cursor()
            notes, _, bars = TJAParser.notes_to_position(TJAParser(self.tja.file_path), self.player_1.difficulty)
            hash = self.tja.hash_note_data(notes, bars)
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
                        session_data.result_total_drumroll, session_data.result_max_combo, int(self.player_1.gauge.gauge_length > self.player_1.gauge.clear_start[min(self.player_1.difficulty, 3)]))
                cursor.execute(insert_query, data)
                con.commit()

    def update(self):
        self.on_screen_start()
        self.transition.update(get_current_ms())
        self.current_ms = get_current_ms() - self.start_ms
        if self.tja is not None:
            if (self.current_ms >= self.tja.metadata.offset*1000 + self.start_delay - global_data.config["general"]["judge_offset"]) and not self.song_started:
                if self.song_music is not None:
                    if not audio.is_sound_playing(self.song_music):
                        audio.play_sound(self.song_music)
                        print(f"Song started at {self.current_ms}")
                if self.movie is not None:
                    self.movie.start(get_current_ms())
                self.song_started = True
        if self.movie is not None:
            self.movie.update()
        else:
            self.background.update(get_current_ms(), self.player_1.gauge.gauge_length > self.player_1.gauge.clear_start[min(self.player_1.difficulty, 3)])

        self.player_1.update(self)
        self.song_info.update(get_current_ms())
        self.result_transition.update(get_current_ms())
        if self.result_transition.is_finished:
            return self.on_screen_end('RESULT')
        elif len(self.player_1.play_notes) == 0:
            session_data.result_score, session_data.result_good, session_data.result_ok, session_data.result_bad, session_data.result_max_combo, session_data.result_total_drumroll = self.player_1.get_result_score()
            session_data.result_gauge_length = self.player_1.gauge.gauge_length
            if self.end_ms != 0:
                if get_current_ms() >= self.end_ms + 8533.34:
                    if not self.result_transition.is_started:
                        self.result_transition.start()
                        audio.play_sound(self.sound_result_transition)
            else:
                self.write_score()
                self.end_ms = get_current_ms()

        if ray.is_key_pressed(ray.KeyboardKey.KEY_F1):
            if self.song_music is not None:
                audio.stop_sound(self.song_music)
            self.init_tja(global_data.selected_song, session_data.selected_difficulty)
            audio.play_sound(self.sound_restart)
            self.song_started = False

        if ray.is_key_pressed(ray.KeyboardKey.KEY_ESCAPE):
            if self.song_music is not None:
                audio.stop_sound(self.song_music)
            return self.on_screen_end('SONG_SELECT')

    def draw(self):
        if self.movie is not None:
            self.movie.draw()
        else:
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

    def __init__(self, game_screen: GameScreen, player_number: int, difficulty: int):

        self.player_number = str(player_number)
        self.difficulty = difficulty
        self.visual_offset = global_data.config["general"]["visual_offset"]

        if game_screen.tja is not None:
            self.play_notes, self.draw_note_list, self.draw_bar_list = game_screen.tja.notes_to_position(self.difficulty)
            self.play_notes, self.draw_note_list, self.draw_bar_list = apply_modifiers(self.play_notes, self.draw_note_list, self.draw_bar_list)
        else:
            self.play_notes, self.draw_note_list, self.draw_bar_list = deque(), deque(), deque()
        self.total_notes = len([note for note in self.play_notes if 0 < note.type < 5])
        self.base_score = calculate_base_score(self.play_notes)

        #Note management
        self.current_bars: list[Note] = []
        self.current_notes_draw: list[Note | Drumroll | Balloon] = []
        self.is_drumroll = False
        self.curr_drumroll_count = 0
        self.is_balloon = False
        self.curr_balloon_count = 0
        self.balloon_index = 0

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
        self.combo_display = Combo(self.combo, get_current_ms())
        self.score_counter = ScoreCounter(self.score)
        plate_info = global_data.config['nameplate']
        self.nameplate = Nameplate(plate_info['name'], plate_info['title'], global_data.player_num, plate_info['dan'], plate_info['gold'])

        self.input_log: dict[float, tuple] = dict()

        if game_screen.tja is not None:
            stars = game_screen.tja.metadata.course_data[self.difficulty].level
        else:
            stars = 0
        self.gauge = Gauge(self.player_number, self.difficulty, stars, self.total_notes)
        self.gauge_hit_effect: list[GaugeHitEffect] = []

        self.autoplay_hit_side = 'L'
        self.last_subdivision = -1

    def get_result_score(self):
        return self.score, self.good_count, self.ok_count, self.bad_count, self.max_combo, self.total_drumroll

    def get_position_x(self, width: int, current_ms: float, load_ms: float, pixels_per_frame: float) -> int:
        return int(width + pixels_per_frame * (60 / 1000) * (load_ms - current_ms) - 64) - self.visual_offset

    def get_position_y(self, current_ms: float, load_ms: float, pixels_per_frame: float, pixels_per_frame_x) -> int:
        return int((pixels_per_frame * (60 / 1000) * (load_ms - current_ms)) + (((1280 - GameScreen.JUDGE_X) * pixels_per_frame) / pixels_per_frame_x))

    def animation_manager(self, animation_list: list):
        if len(animation_list) <= 0:
            return

        for i in range(len(animation_list)-1, -1, -1):
            animation = animation_list[i]
            animation.update(get_current_ms())
            if animation.is_finished:
                animation_list.pop(i)

    def bar_manager(self, game_screen: GameScreen):
        #Add bar to current_bars list if it is ready to be shown on screen
        if len(self.draw_bar_list) > 0 and game_screen.current_ms > self.draw_bar_list[0].load_ms:
            self.current_bars.append(self.draw_bar_list.popleft())

        #If a bar is off screen, remove it
        if len(self.current_bars) == 0:
            return

        for i in range(len(self.current_bars)-1, -1, -1):
            bar = self.current_bars[i]
            position = self.get_position_x(game_screen.width, game_screen.current_ms, bar.hit_ms, bar.pixels_per_frame_x)
            if position < GameScreen.JUDGE_X + 650:
                self.current_bars.pop(i)

    def play_note_manager(self, game_screen: GameScreen):
        if len(self.play_notes) == 0:
            return

        note = self.play_notes[0]
        if note.hit_ms + Player.TIMING_BAD < game_screen.current_ms:
            if 0 < note.type <= 4:
                self.combo = 0
                self.bad_count += 1
                self.gauge.add_bad()
                self.play_notes.popleft()
            elif note.type != 8:
                tail = self.play_notes[1]
                if tail.hit_ms <= game_screen.current_ms:
                    self.play_notes.popleft()
                    self.play_notes.popleft()
                    self.is_drumroll = False
                    self.is_balloon = False
            else:
                if len(self.play_notes) == 1:
                    self.play_notes.popleft()
        elif (note.hit_ms <= game_screen.current_ms):
            if note.type == 5 or note.type == 6:
                self.is_drumroll = True
            elif note.type == 7 or note.type == 9:
                self.is_balloon = True

    def draw_note_manager(self, game_screen: GameScreen):
        if len(self.draw_note_list) > 0 and game_screen.current_ms + 1000 >= self.draw_note_list[0].load_ms:
            current_note = self.draw_note_list.popleft()
            if 5 <= current_note.type <= 7:
                bisect.insort_left(self.current_notes_draw, current_note, key=lambda x: x.index)
                try:
                    tail_note = next(note for note in self.draw_note_list if note.type == 8)
                    bisect.insort_left(self.current_notes_draw, tail_note, key=lambda x: x.index)
                    self.draw_note_list.remove(tail_note)
                except Exception as e:
                    raise(e)
            else:
                bisect.insort_left(self.current_notes_draw, current_note, key=lambda x: x.index)

        if len(self.current_notes_draw) == 0:
            return

        if isinstance(self.current_notes_draw[0], Drumroll) and 255 > self.current_notes_draw[0].color > 0:
            self.current_notes_draw[0].color += 1

        note = self.current_notes_draw[0]
        if note.type in {5, 6, 7} and len(self.current_notes_draw) > 1:
            note = self.current_notes_draw[1]
        position = self.get_position_x(game_screen.width, game_screen.current_ms, note.hit_ms, note.pixels_per_frame_x)
        if position < GameScreen.JUDGE_X + 650:
            self.current_notes_draw.pop(0)

    def note_manager(self, game_screen: GameScreen):
        self.bar_manager(game_screen)
        self.play_note_manager(game_screen)
        self.draw_note_manager(game_screen)

    def note_correct(self, note: Note):
        self.play_notes.popleft()
        index = note.index
        if note.type == 7:
            self.play_notes.popleft()

        if note.type < 7:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

        if note.type != 9:
            self.draw_arc_list.append(NoteArc(note.type, get_current_ms(), 1, note.type == 3 or note.type == 4) or note.type == 7)

        if note in self.current_notes_draw:
            index = self.current_notes_draw.index(note)
            self.current_notes_draw.pop(index)

    def check_drumroll(self, drum_type: int):
        self.draw_arc_list.append(NoteArc(drum_type, get_current_ms(), 1, drum_type == 3 or drum_type == 4))
        self.curr_drumroll_count += 1
        self.total_drumroll += 1
        self.score += 100
        self.base_score_list.append(ScoreCounterAnimation(self.player_number, 100))
        if not isinstance(self.current_notes_draw[0], Drumroll):
            return
        self.current_notes_draw[0].color = max(0, 255 - (self.curr_drumroll_count * 10))

    def check_balloon(self, game_screen: GameScreen, drum_type: int, note: Balloon):
        if drum_type != 1:
            return
        if note.is_kusudama:
            self.check_kusudama(game_screen, note)
            return
        if self.balloon_anim is None:
            self.balloon_anim = BalloonAnimation(get_current_ms(), note.count)
        self.curr_balloon_count += 1
        self.total_drumroll += 1
        self.score += 100
        self.base_score_list.append(ScoreCounterAnimation(self.player_number, 100))
        if self.curr_balloon_count == note.count:
            self.is_balloon = False
            note.popped = True
            self.balloon_anim.update(get_current_ms(), self.curr_balloon_count, note.popped)
            audio.play_sound(game_screen.sound_balloon_pop)
            self.note_correct(self.play_notes[0])

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

    def check_note(self, game_screen: GameScreen, drum_type: int):
        if len(self.play_notes) == 0:
            return

        curr_note = self.play_notes[0]
        if self.is_drumroll:
            self.check_drumroll(drum_type)
        elif self.is_balloon:
            if not isinstance(curr_note, Balloon):
                raise Exception("Balloon mode entered but current note is not balloon")
            self.check_balloon(game_screen, drum_type, curr_note)
        else:
            self.curr_drumroll_count = 0
            self.curr_balloon_count = 0
            curr_note = next(
                (note for note in self.play_notes if note.type not in {5, 6, 7, 8}),
                None  # Default if no matching note is found
            )
            if curr_note is None:
                return
            #If the wrong key was hit, stop checking
            if drum_type == 1 and curr_note.type not in {1, 3}:
                return
            if drum_type == 2 and curr_note.type not in {2, 4}:
                return
            #If the note is too far away, stop checking
            if game_screen.current_ms > (curr_note.hit_ms + Player.TIMING_BAD):
                return
            big = curr_note.type == 3 or curr_note.type == 4
            if (curr_note.hit_ms - Player.TIMING_GOOD) <= game_screen.current_ms <= (curr_note.hit_ms + Player.TIMING_GOOD):
                self.draw_judge_list.append(Judgement('GOOD', big, ms_display=game_screen.current_ms - curr_note.hit_ms))
                self.lane_hit_effect = LaneHitEffect('GOOD')
                self.good_count += 1
                self.score += self.base_score
                self.base_score_list.append(ScoreCounterAnimation(self.player_number, self.base_score))
                self.note_correct(curr_note)
                self.gauge.add_good()

            elif (curr_note.hit_ms - Player.TIMING_OK) <= game_screen.current_ms <= (curr_note.hit_ms + Player.TIMING_OK):
                self.draw_judge_list.append(Judgement('OK', big, ms_display=game_screen.current_ms - curr_note.hit_ms))
                self.ok_count += 1
                self.score += 10 * math.floor(self.base_score / 2 / 10)
                self.base_score_list.append(ScoreCounterAnimation(self.player_number, 10 * math.floor(self.base_score / 2 / 10)))
                self.note_correct(curr_note)
                self.gauge.add_ok()

            elif (curr_note.hit_ms - Player.TIMING_BAD) <= game_screen.current_ms <= (curr_note.hit_ms + Player.TIMING_BAD):
                self.draw_judge_list.append(Judgement('BAD', big, ms_display=game_screen.current_ms - curr_note.hit_ms))
                self.bad_count += 1
                self.combo = 0
                self.play_notes.popleft()
                self.gauge.add_bad()

    def drumroll_counter_manager(self):
        if self.is_drumroll and self.curr_drumroll_count > 0 and self.drumroll_counter is None:
            self.drumroll_counter = DrumrollCounter(get_current_ms())

        if self.drumroll_counter is not None:
            if self.drumroll_counter.is_finished and not self.is_drumroll:
                self.drumroll_counter = None
            else:
                self.drumroll_counter.update(get_current_ms(), self.curr_drumroll_count)

    def balloon_manager(self):
        if self.balloon_anim is not None:
            self.balloon_anim.update(get_current_ms(), self.curr_balloon_count, not self.is_balloon)
            if self.balloon_anim.is_finished:
                self.balloon_anim = None
        if self.kusudama_anim is not None:
            self.kusudama_anim.update(get_current_ms(), not self.is_balloon)
            self.kusudama_anim.update_count(self.curr_balloon_count)
            if self.kusudama_anim.is_finished:
                self.kusudama_anim = None

    def handle_input(self, game_screen: GameScreen):
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

                self.check_note(game_screen, 1 if note_type == 'DON' else 2)
                self.input_log[game_screen.current_ms] = (note_type, side)

    def autoplay_manager(self, game_screen: GameScreen):
        if not global_data.modifiers.auto:
            return
        if len(self.play_notes) == 0:
            return
        note = self.play_notes[0]
        if self.is_drumroll or self.is_balloon:
            if self.play_notes[0].bpm == 0:
                subdivision_in_ms = 0
            else:
                subdivision_in_ms = game_screen.current_ms // ((60000 * 4 / self.play_notes[0].bpm) / 24)
            if subdivision_in_ms > self.last_subdivision:
                self.last_subdivision = subdivision_in_ms
                hit_type = 'DON'
                self.lane_hit_effect = LaneHitEffect(hit_type)
                if self.autoplay_hit_side == 'L':
                    self.autoplay_hit_side = 'R'
                else:
                    self.autoplay_hit_side = 'L'
                self.draw_drum_hit_list.append(DrumHitEffect(hit_type, self.autoplay_hit_side))
                audio.play_sound(game_screen.sound_don)
                type = note.type
                if type == 6:
                    type = 3
                else:
                    type = 1
                self.check_note(game_screen, type)
        else:
            while game_screen.current_ms >= note.hit_ms and note.type <= 4:
                hit_type = 'DON'
                if note.type == 2 or note.type == 4:
                    hit_type = 'KAT'
                self.lane_hit_effect = LaneHitEffect(hit_type)
                if self.autoplay_hit_side == 'L':
                    self.autoplay_hit_side = 'R'
                else:
                    self.autoplay_hit_side = 'L'
                self.draw_drum_hit_list.append(DrumHitEffect(hit_type, self.autoplay_hit_side))
                sound = game_screen.sound_don if hit_type == "DON" else game_screen.sound_kat
                audio.play_sound(sound)
                type = note.type
                if type == 6 or type == 9:
                    type = 3
                elif type == 5 or type == 7:
                    type = 1
                self.check_note(game_screen, type)
                if len(self.play_notes) > 0:
                    note = self.play_notes[0]
                else:
                    break


    def update(self, game_screen: GameScreen):
        self.note_manager(game_screen)
        self.combo_display.update(get_current_ms(), self.combo)
        self.drumroll_counter_manager()
        self.animation_manager(self.draw_judge_list)
        self.balloon_manager()
        if self.lane_hit_effect is not None:
            self.lane_hit_effect.update(get_current_ms())
        self.animation_manager(self.draw_drum_hit_list)
        for anim in self.draw_arc_list:
            anim.update(get_current_ms())
            if anim.is_finished:
                self.gauge_hit_effect.append(GaugeHitEffect(anim.note_type, anim.is_big))
                self.draw_arc_list.remove(anim)
        self.animation_manager(self.gauge_hit_effect)
        self.animation_manager(self.base_score_list)
        self.score_counter.update(get_current_ms(), self.score)
        self.autoplay_manager(game_screen)
        self.handle_input(game_screen)
        self.nameplate.update(get_current_ms())
        self.gauge.update(get_current_ms())

    def draw_drumroll(self, game_screen: GameScreen, head: Drumroll, current_eighth: int):
        start_position = self.get_position_x(game_screen.width, game_screen.current_ms, head.load_ms, head.pixels_per_frame_x)
        tail = next((note for note in self.current_notes_draw[1:] if note.type == 8 and note.index > head.index), self.current_notes_draw[1])
        is_big = int(head.type == 6)
        end_position = self.get_position_x(game_screen.width, game_screen.current_ms, tail.load_ms, tail.pixels_per_frame_x)
        length = end_position - start_position
        color = ray.Color(255, head.color, head.color, 255)
        if head.display:
            tex.draw_texture('notes', "8", frame=is_big, x=start_position+64, y=192, x2=length-64-32, color=color)
            if is_big:
                tex.draw_texture('notes', "drumroll_big_tail", x=end_position, y=192, color=color)
            else:
                tex.draw_texture('notes', "drumroll_tail", x=end_position, y=192, color=color)
            tex.draw_texture('notes', str(head.type), frame=current_eighth % 2, x=start_position, y=192, color=color)

        tex.draw_texture('notes', 'moji_drumroll_mid', x=start_position + 60, y=323, x2=length)
        tex.draw_texture('notes', 'moji', frame=head.moji, x=(start_position - (168//2)) + 64, y=323)
        tex.draw_texture('notes', 'moji', frame=tail.moji, x=(end_position - (168//2)) + 32, y=323)

    def draw_balloon(self, game_screen: GameScreen, head: Balloon, current_eighth: int):
        offset = 12
        start_position = self.get_position_x(game_screen.width, game_screen.current_ms, head.load_ms, head.pixels_per_frame_x)
        tail = next((note for note in self.current_notes_draw[1:] if note.type == 8 and note.index > head.index), self.current_notes_draw[1])
        end_position = self.get_position_x(game_screen.width, game_screen.current_ms, tail.load_ms, tail.pixels_per_frame_x)
        pause_position = 349
        if game_screen.current_ms >= tail.hit_ms:
            position = end_position
        elif game_screen.current_ms >= head.hit_ms:
            position = pause_position
        else:
            position = start_position
        if head.display:
            tex.draw_texture('notes', str(head.type), frame=current_eighth % 2, x=position-offset, y=192)
        tex.draw_texture('notes', '10', frame=current_eighth % 2, x=position-offset+128, y=192)

    def draw_bars(self, game_screen: GameScreen):
        if len(self.current_bars) <= 0:
            return

        for bar in reversed(self.current_bars):
            if not bar.display:
                continue
            x_position = self.get_position_x(game_screen.width, game_screen.current_ms, bar.load_ms, bar.pixels_per_frame_x)
            y_position = self.get_position_y(game_screen.current_ms, bar.load_ms, bar.pixels_per_frame_y, bar.pixels_per_frame_x)
            tex.draw_texture('notes', str(bar.type), x=x_position+60, y=y_position+190)

    def draw_notes(self, game_screen: GameScreen):
        if len(self.current_notes_draw) <= 0:
            return

        if len(self.current_bars) > 0:
            if self.current_bars[0].bpm == 0:
                eighth_in_ms = 0
            else:
                eighth_in_ms = (60000 * 4 / self.current_bars[0].bpm) / 8
        else:
            if self.current_notes_draw[0].bpm == 0:
                eighth_in_ms = 0
            else:
                eighth_in_ms = (60000 * 4 / self.current_notes_draw[0].bpm) / 8
        current_eighth = 0
        if self.combo >= 50 and eighth_in_ms != 0:
            current_eighth = int((game_screen.current_ms - game_screen.start_ms) // eighth_in_ms)

        for note in reversed(self.current_notes_draw):
            if self.is_balloon and note == self.current_notes_draw[0]:
                continue
            if note.type == 8:
                continue
            x_position = self.get_position_x(game_screen.width, game_screen.current_ms, note.load_ms, note.pixels_per_frame_x)
            y_position = self.get_position_y(game_screen.current_ms, note.load_ms, note.pixels_per_frame_y, note.pixels_per_frame_x)
            if isinstance(note, Drumroll):
                self.draw_drumroll(game_screen, note, current_eighth)
            elif isinstance(note, Balloon) and not note.is_kusudama:
                self.draw_balloon(game_screen, note, current_eighth)
                tex.draw_texture('notes', 'moji', frame=note.moji, x=x_position - (168//2) + 64, y=323 + y_position)
            else:
                if note.display:
                    tex.draw_texture('notes', str(note.type), frame=current_eighth % 2, x=x_position, y=y_position+192, center=True)
                tex.draw_texture('notes', 'moji', frame=note.moji, x=x_position - (168//2) + 64, y=323 + y_position)

    def draw_modifiers(self):
        tex.draw_texture('lane', 'mod_shinuchi')
        if global_data.modifiers.speed >= 4:
            tex.draw_texture('lane', 'mod_yonbai')
        elif global_data.modifiers.speed >= 3:
            tex.draw_texture('lane', 'mod_sanbai')
        elif global_data.modifiers.speed > 1:
            tex.draw_texture('lane', 'mod_baisaku')
        if global_data.modifiers.display:
            tex.draw_texture('lane', 'mod_doron')
        if global_data.modifiers.inverse:
            tex.draw_texture('lane', 'mod_abekobe')
        if global_data.modifiers.random == 2:
            tex.draw_texture('lane', 'mod_detarame')
        elif global_data.modifiers.random == 1:
            tex.draw_texture('lane', 'mod_kimagure')

    def draw(self, game_screen: GameScreen):
        tex.draw_texture('lane', 'lane_background')
        self.gauge.draw()
        if self.lane_hit_effect is not None:
            self.lane_hit_effect.draw()
        tex.draw_texture('lane', 'lane_hit_circle')
        for anim in self.draw_judge_list:
            anim.draw()
        self.draw_bars(game_screen)
        self.draw_notes(game_screen)
        tex.draw_texture('lane', f'{self.player_number}p_lane_cover')
        tex.draw_texture('lane', 'drum')
        if global_data.modifiers.auto:
            tex.draw_texture('lane', 'auto_icon')
        for anim in self.draw_drum_hit_list:
            anim.draw()
        self.combo_display.draw()
        tex.draw_texture('lane', 'lane_score_cover')
        tex.draw_texture('lane', f'{self.player_number}p_icon')
        tex.draw_texture('lane', 'lane_difficulty', frame=self.difficulty)
        self.nameplate.draw(-62, 285)
        self.draw_modifiers()
        if self.drumroll_counter is not None:
            self.drumroll_counter.draw()
        for anim in self.draw_arc_list:
            anim.draw()
        for anim in self.gauge_hit_effect:
            anim.draw()
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
        self.fade_animation_1.update(current_ms)
        self.fade_animation_2.update(current_ms)
        self.move_animation.update(current_ms)
        self.texture_animation.update(current_ms)

        if self.fade_animation_2.is_finished:
            self.is_finished = True

    def draw(self):
        y = self.move_animation.attribute
        index = int(self.texture_animation.attribute)
        hit_color = ray.fade(ray.WHITE, self.fade_animation_1.attribute)
        color = ray.fade(ray.WHITE, self.fade_animation_2.attribute)
        if self.curr_hit_ms is not None:
            if float(self.curr_hit_ms) < -(global_data.config['general']['hard_judge']):
                color = ray.fade(ray.BLUE, self.fade_animation_2.attribute)
            elif float(self.curr_hit_ms) > (global_data.config['general']['hard_judge']):
                color = ray.fade(ray.RED, self.fade_animation_2.attribute)
        if self.type == 'GOOD':
            if self.big:
                tex.draw_texture('hit_effect', 'hit_effect_good_big', color=color)
                tex.draw_texture('hit_effect', 'outer_good_big', frame=index, color=hit_color)
            else:
                tex.draw_texture('hit_effect', 'hit_effect_good', color=color)
                tex.draw_texture('hit_effect', 'outer_good', frame=index, color=hit_color)
            tex.draw_texture('hit_effect', 'judge_good', y=y, color=color)
        elif self.type == 'OK':
            if self.big:
                tex.draw_texture('hit_effect', 'hit_effect_ok_big', color=color)
                tex.draw_texture('hit_effect', 'outer_ok_big', frame=index, color=hit_color)
            else:
                tex.draw_texture('hit_effect', 'hit_effect_ok', color=color)
                tex.draw_texture('hit_effect', 'outer_ok', frame=index, color=hit_color)
            tex.draw_texture('hit_effect', 'judge_ok', y=y, color=color)
        elif self.type == 'BAD':
            tex.draw_texture('hit_effect', 'judge_bad', y=y, color=color)

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
    def update(self, current_ms):
        self.texture_change.update(current_ms)
        self.circle_fadein.update(current_ms)
        self.fade_out.update(current_ms)
        self.resize.update(current_ms)
        self.rotation.update(current_ms)
        color = ray.YELLOW
        if self.circle_fadein.is_finished:
            color = ray.WHITE
        self.color = ray.fade(color, min(self.fade_out.attribute, self.circle_fadein.attribute))
        if self.fade_out.is_finished:
            self.is_finished = True
    def draw(self):
        color_map = {0.70: ray.WHITE, 0.80: ray.YELLOW, 0.90: ray.ORANGE, 1.00: ray.RED}
        texture_color = ray.WHITE
        for upper_bound, color in color_map.items():
            lower_bound = list(color_map.keys())[list(color_map.keys()).index(upper_bound) - 1] if list(color_map.keys()).index(upper_bound) > 0 else 0.70

            if lower_bound <= self.resize.attribute <= upper_bound:
                texture_color = color
            elif self.resize.attribute >= upper_bound:
                texture_color = ray.RED
        dest_width = 152 * self.resize.attribute
        dest_height = 152 * self.resize.attribute
        origin = ray.Vector2(dest_width / 2, dest_height / 2)
        rotation = self.rotation.attribute*100
        tex.draw_texture('gauge', 'hit_effect', frame=self.texture_change.attribute, x2=-152 + (152 * self.resize.attribute), y2=-152 + (152 * self.resize.attribute), color=ray.fade(texture_color, self.fade_out.attribute), origin=origin, rotation=rotation, center=True)
        tex.draw_texture('notes', str(self.note_type), x=1158, y=101, fade=self.fade_out.attribute)
        if self.is_big:
            tex.draw_texture('gauge', 'hit_effect_circle_big', color=self.color)
        else:
            tex.draw_texture('gauge', 'hit_effect_circle', color=self.color)

class NoteArc:
    def __init__(self, note_type: int, current_ms: float, player_number: int, big: bool):
        self.note_type = note_type
        self.is_big = big
        self.arc_points = 22
        self.create_ms = current_ms
        self.player_number = player_number
        curve_height = 425

        self.start_x, self.start_y = 350, 192
        self.end_x, self.end_y = 1158, 101

        if self.player_number == 1:
            # Control point influences the curve shape
            self.control_x = (self.start_x + self.end_x) // 2
            self.control_y = min(self.start_y, self.end_y) - curve_height  # Arc upward
        else:
            # For player 2 (assumed to be a downward arc)
            self.control_x = (self.start_x + self.end_x) // 2
            self.control_y = max(self.start_y, self.end_y) + curve_height  # Arc downward

        self.x_i = self.start_x
        self.y_i = self.start_y
        self.is_finished = False

        num_precalc_points = 100  # More points for better approximation
        self.path_points = []
        self.path_distances = [0.0]  # Cumulative distance at each point

        prev_x, prev_y = self.start_x, self.start_y
        total_distance = 0.0

        for i in range(1, num_precalc_points + 1):
            t = i / num_precalc_points
            x = int((1-t)**2 * self.start_x + 2*(1-t)*t * self.control_x + t**2 * self.end_x)
            y = int((1-t)**2 * self.start_y + 2*(1-t)*t * self.control_y + t**2 * self.end_y)

            # Calculate distance from previous point
            dx = x - prev_x
            dy = y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)
            total_distance += distance

            self.path_points.append((x, y))
            self.path_distances.append(total_distance)

            prev_x, prev_y = x, y

        self.total_path_length = total_distance
        self.x_i = self.start_x
        self.y_i = self.start_y
        self.is_finished = False

    def update(self, current_ms: float):
        if self.x_i >= self.end_x:
            self.is_finished = True
            self.x_i = self.end_x
            self.y_i = self.end_y
            return

        ms_since_call = (current_ms - self.create_ms) / 16.67
        ms_since_call = max(0, min(ms_since_call, self.arc_points))

        # Calculate desired distance along the path (constant speed)
        target_distance = (ms_since_call / self.arc_points) * self.total_path_length

        # Find the closest pre-calculated points
        index = 0
        while index < len(self.path_distances) - 1 and self.path_distances[index + 1] < target_distance:
            index += 1

        # Interpolate between the points
        if index < len(self.path_distances) - 1:
            d1 = self.path_distances[index]
            d2 = self.path_distances[index + 1]
            if d2 > d1:  # Avoid division by zero
                fraction = (target_distance - d1) / (d2 - d1)
                x1, y1 = self.path_points[index - 1] if index > 0 else (self.start_x, self.start_y)
                x2, y2 = self.path_points[index]
                self.x_i = int(x1 + fraction * (x2 - x1))
                self.y_i = int(y1 + fraction * (y2 - y1))
        else:
            # At the end of the path
            self.x_i = self.end_x
            self.y_i = self.end_y

    def draw(self):
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
        for i in range(len(counter)):
            tex.draw_texture('drumroll_counter', 'counter', color=color, frame=int(counter[i]), x=-(total_width//2)+(i*52), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)

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
            tex.draw_texture('balloon', 'pop', frame=balloon_index, color=self.color)
        if self.balloon_count > 0:
            tex.draw_texture('balloon', 'bubble')
            counter = str(max(0, self.balloon_total - self.balloon_count + 1))
            total_width = len(counter) * 52
            for i in range(len(counter)):
                tex.draw_texture('balloon', 'counter', frame=int(counter[i]), color=self.color, x=-(total_width // 2) + (i * 52), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)

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
            for i in range(len(counter)):
                tex.draw_texture('kusudama', 'counter', frame=int(counter[i]), x=-(total_width // 2) + (i * 150), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)

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
        counter = str(self.combo)
        if self.combo < 3:
            return
        if self.combo < 100:
            margin = 30
            total_width = len(counter) * margin
            tex.draw_texture('combo', 'combo')
            for i in range(len(counter)):
                tex.draw_texture('combo', 'counter', frame=int(counter[i]), x=-(total_width // 2) + (i * margin), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)
        else:
            margin = 35
            total_width = len(counter) * margin
            tex.draw_texture('combo', 'combo_100')
            for i in range(len(counter)):
                tex.draw_texture('combo', 'counter_100', frame=int(counter[i]), x=-(total_width // 2) + (i * margin), y=-self.stretch_animation.attribute, y2=self.stretch_animation.attribute)
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
        counter = str(self.score)
        x, y = 150, 185
        margin = 20
        total_width = len(counter) * margin
        start_x = x - total_width
        for i in range(len(counter)):
            tex.draw_texture('lane', 'score_number', frame=int(counter[i]), x=start_x + (i * margin), y=y - self.stretch.attribute, y2=self.stretch.attribute)

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
            self.color = ray.fade(ray.Color(84, 250, 238, 255), 1.0)
        else:
            self.color = ray.fade(ray.Color(254, 102, 0, 255), 1.0)
        self.is_finished = False
        self.y_pos_list = []

    def update(self, current_ms: float):
        self.fade_animation_1.update(current_ms)
        self.move_animation_1.update(current_ms)
        self.move_animation_2.update(current_ms)
        self.move_animation_3.update(current_ms)
        self.move_animation_4.update(current_ms)
        self.fade_animation_2.update(current_ms)

        if self.fade_animation_1.is_finished:
            self.color = ray.fade(self.color, self.fade_animation_2.attribute)
        else:
            self.color = ray.fade(self.color, self.fade_animation_1.attribute)
        if self.fade_animation_2.is_finished:
            self.is_finished = True
        self.y_pos_list = []
        for i in range(1, len(str(self.counter))+1):
            self.y_pos_list.append(self.move_animation_4.attribute + i*5)

    def draw(self):
        if self.move_animation_1.is_finished:
            x = self.move_animation_2.attribute
        else:
            x = self.move_animation_1.attribute
        if x == 0:
            return
        counter = str(self.counter)
        margin = 20
        total_width = len(counter) * margin
        start_x = x - total_width
        for i in range(len(counter)):
            if self.move_animation_3.is_finished:
                y = self.y_pos_list[i]
            elif self.move_animation_2.is_finished:
                y = self.move_animation_3.attribute
            else:
                y = 148
            tex.draw_texture('lane', 'score_number', frame=int(counter[i]), x=start_x + (i * margin), y=y, color=self.color)

class SongInfo:
    def __init__(self, song_name: str, genre: str):
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

class ResultTransition:
    def __init__(self, player_num: int):
        self.player_num = player_num
        self.move = global_data.tex.get_animation(5)
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
            global_data.tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter', frame=0, x=x, y=-720 + self.move.attribute)
            global_data.tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter', frame=0, x=x, y=720 - self.move.attribute)
            global_data.tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter_footer', x=x, y=-432 + self.move.attribute)
            global_data.tex.draw_texture('result_transition', f'{str(self.player_num)}p_shutter_footer', x=x, y=1008 - self.move.attribute)
            x += 256

class Gauge:
    def __init__(self, player_num: str, difficulty: int, level: int, total_notes: int):
        self.player_num = player_num
        self.gauge_length = 0
        self.previous_length = 0
        self.total_notes = total_notes
        self.difficulty = min(3, difficulty)
        self.clear_start = [68, 68, 68, 68]
        self.level = min(10, level)
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
        if self.gauge_length > 87:
            self.gauge_length = 87

    def add_ok(self):
        self.gauge_update_anim.start()
        self.previous_length = int(self.gauge_length)
        self.gauge_length += ((1 * self.table[self.difficulty][self.level]["ok_multiplier"]) / self.total_notes) * (100 * (self.clear_start[self.difficulty] / self.table[self.difficulty][self.level]["clear_rate"]))
        if self.gauge_length > 87:
            self.gauge_length = 87

    def add_bad(self):
        self.previous_length = int(self.gauge_length)
        self.gauge_length += ((1 * self.table[self.difficulty][self.level]["bad_multiplier"]) / self.total_notes) * (100 * (self.clear_start[self.difficulty] / self.table[self.difficulty][self.level]["clear_rate"]))
        if self.gauge_length < 0:
            self.gauge_length = 0

    def update(self, current_ms: float):
        if self.gauge_length == 87 and self.rainbow_fade_in is None:
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
        tex.draw_texture('gauge', 'border')
        tex.draw_texture('gauge', f'{self.player_num}p_unfilled')
        gauge_length = int(self.gauge_length)
        for i in range(gauge_length):
            if i == 68:
                tex.draw_texture('gauge', 'bar_clear_transition', x=i*8)
            elif i > 68:
                tex.draw_texture('gauge', 'bar_clear_top', x=i*8)
                tex.draw_texture('gauge', 'bar_clear_bottom', x=i*8)
            else:
                tex.draw_texture('gauge', f'{self.player_num}p_bar', x=i*8)
        if gauge_length == 87 and self.rainbow_fade_in is not None and self.rainbow_animation is not None:
            if 0 < self.rainbow_animation.attribute < 8:
                tex.draw_texture('gauge', 'rainbow', frame=self.rainbow_animation.attribute-1, fade=self.rainbow_fade_in.attribute)
            tex.draw_texture('gauge', 'rainbow', frame=self.rainbow_animation.attribute, fade=self.rainbow_fade_in.attribute)
        if self.gauge_update_anim is not None and gauge_length < 88 and gauge_length > self.previous_length:
            if gauge_length == 69:
                tex.draw_texture('gauge', 'bar_clear_transition_fade', x=gauge_length*8, fade=self.gauge_update_anim.attribute)
            elif gauge_length > 69:
                tex.draw_texture('gauge', 'bar_clear_fade', x=gauge_length*8, fade=self.gauge_update_anim.attribute)
            else:
                tex.draw_texture('gauge', f'{self.player_num}p_bar_fade', x=gauge_length*8, fade=self.gauge_update_anim.attribute)
        tex.draw_texture('gauge', 'overlay', fade=0.15)
        if gauge_length >= 69:
            tex.draw_texture('gauge', 'clear')
            tex.draw_texture('gauge', 'tamashii')
        else:
            tex.draw_texture('gauge', 'clear_dark')
            tex.draw_texture('gauge', 'tamashii_dark')
