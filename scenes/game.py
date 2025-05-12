import bisect
import math
import sqlite3
from pathlib import Path
from typing import Optional

import pyray as ray

from libs.animation import Animation
from libs.audio import audio
from libs.backgrounds import Background
from libs.tja import Balloon, Drumroll, Note, TJAParser, calculate_base_score
from libs.utils import (
    OutlinedText,
    get_config,
    get_current_ms,
    global_data,
    load_all_textures_from_zip,
    load_image_from_zip,
    load_texture_from_zip,
    session_data,
)
from libs.video import VideoPlayer


class GameScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.judge_x = 414
        self.current_ms = 0
        self.result_transition = None
        self.song_info = None
        self.screen_init = False
        self.movie = None
        self.end_ms = 0
        self.start_delay = 1000
        self.song_started = False

        self.background = Background(width, height)

    def load_textures(self):
        self.textures = load_all_textures_from_zip(Path('Graphics/lumendata/enso_system/common.zip'))
        zip_file = Path('Graphics/lumendata/enso_system/common.zip')

        image = load_image_from_zip(zip_file, 'lane_img00000.png')
        ray.image_resize(image, 948, 176)
        ray.unload_texture(self.textures['lane'][0])
        self.textures['lane'][0] = ray.load_texture_from_image(image)

        image = load_image_from_zip(zip_file, 'lane_hit_img00005.png')
        ray.image_resize(image, 951, 130)
        ray.unload_texture(self.textures['lane_hit'][5])
        self.textures['lane_hit'][5] = ray.load_texture_from_image(image)
        image = load_image_from_zip(zip_file, 'lane_hit_img00006.png')
        ray.image_resize(image, 951, 130)
        ray.unload_texture(self.textures['lane_hit'][6])
        self.textures['lane_hit'][6] = ray.load_texture_from_image(image)
        image = load_image_from_zip(zip_file, 'lane_hit_img00007.png')
        ray.image_resize(image, 951, 130)
        ray.unload_texture(self.textures['lane_hit'][7])
        self.textures['lane_hit'][7] = ray.load_texture_from_image(image)

        self.texture_combo_text = [load_texture_from_zip(zip_file, 'lane_obi_img00035.png'),
        load_texture_from_zip(zip_file, 'lane_obi_img00046.png')]
        self.texture_combo_numbers = []
        for i in range(36, 58):
            if i not in [46, 48]:
                filename = f'lane_obi_img{str(i).zfill(5)}.png'
                self.texture_combo_numbers.append(load_texture_from_zip(zip_file, filename))
        self.texture_combo_glimmer = load_texture_from_zip(zip_file, 'lane_obi_img00048.png')

        self.texture_se_moji = []
        for i in range(0, 17):
            filename = f'onp_moji_img{str(i).zfill(5)}.png'
            if i == 8:
                filename = 'onp_renda_moji_img00001.png'
            self.texture_se_moji.append(load_texture_from_zip(zip_file, filename))

        self.textures.update(load_all_textures_from_zip(Path('Graphics/lumendata/enso_system/base1p.zip')))
        self.textures.update(load_all_textures_from_zip(Path('Graphics/lumendata/enso_system/don1p.zip')))


        self.result_transition_1 = load_texture_from_zip(Path('Graphics/lumendata/enso_result.zip'), 'retry_game_img00125.png')
        self.result_transition_2 = load_texture_from_zip(Path('Graphics/lumendata/enso_result.zip'), 'retry_game_img00126.png')

    def load_sounds(self):
        sounds_dir = Path("Sounds")
        self.sound_don = audio.load_sound(str(sounds_dir / "inst_00_don.wav"))
        self.sound_kat = audio.load_sound(str(sounds_dir / "inst_00_katsu.wav"))
        self.sound_balloon_pop = audio.load_sound(str(sounds_dir / "balloon_pop.wav"))
        self.sound_result_transition = audio.load_sound(str(sounds_dir / "result" / "VO_RESULT [1].ogg"))
        self.sounds = [self.sound_don, self.sound_kat, self.sound_balloon_pop, self.sound_result_transition]

    def init_tja(self, song: str, difficulty: int):
        self.load_textures()
        self.load_sounds()

        #Map notes to textures
        self.note_type_list = [self.textures['lane_syousetsu'][0],
            self.textures['onp_don'], self.textures['onp_katsu'],
            self.textures['onp_don_dai'], self.textures['onp_katsu_dai'],
            [self.textures['onp_renda'][2], self.textures['onp_renda'][3]],
            [self.textures['onp_renda_dai'][2], self.textures['onp_renda_dai'][3]],
            [self.textures['onp_fusen'][1], self.textures['onp_fusen'][2]],
            self.textures['onp_renda'][0], self.textures['onp_renda'][1],
            self.textures['onp_renda_dai'][0], self.textures['onp_renda_dai'][1],
            self.textures['onp_fusen'][0]]

        self.tja = TJAParser(song, start_delay=self.start_delay)
        metadata = self.tja.get_metadata()
        if hasattr(self.tja, 'bg_movie'):
            if Path(self.tja.bg_movie).exists():
                self.movie = VideoPlayer(str(Path(self.tja.bg_movie)))
                self.movie.set_volume(0.0)
        else:
            self.movie = None
        self.tja.distance = self.width - self.judge_x
        session_data.song_title = self.tja.title

        self.player_1 = Player(self, 1, difficulty, metadata, get_config()["general"]["judge_offset"])
        self.song_music = audio.load_sound(str(Path(self.tja.wave)))
        self.start_ms = (get_current_ms() - self.tja.offset*1000)

    def on_screen_start(self):
        if not self.screen_init:
            self.screen_init = True
            self.init_tja(session_data.selected_song, session_data.selected_difficulty)
            self.song_info = SongInfo(self.tja.title, 'TEST')
            self.result_transition = None

    def on_screen_end(self):
        self.screen_init = False
        for zip in self.textures:
            for texture in self.textures[zip]:
                ray.unload_texture(texture)
        self.song_started = False
        self.end_ms = 0
        return 'RESULT'

    def write_score(self):
        if get_config()['general']['autoplay']:
            return
        with sqlite3.connect('scores.db') as con:
            cursor = con.cursor()
            hash = self.tja.hash_note_data(self.tja.data_to_notes(self.player_1.difficulty)[0])
            check_query = "SELECT score FROM Scores WHERE hash = ? LIMIT 1"
            cursor.execute(check_query, (hash,))
            result = cursor.fetchone()
            if result is None or session_data.result_score > result[0]:
                insert_query = '''
                INSERT OR REPLACE INTO Scores (hash, en_name, jp_name, diff, score, good, ok, bad, drumroll, combo)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                '''
                data = (hash, self.tja.title,
                        self.tja.title_ja, self.player_1.difficulty,
                        session_data.result_score, session_data.result_good,
                        session_data.result_ok, session_data.result_bad,
                        session_data.result_total_drumroll, session_data.result_max_combo)
                cursor.execute(insert_query, data)
                con.commit()

    def update(self):
        self.on_screen_start()
        self.current_ms = get_current_ms() - self.start_ms
        if (self.current_ms >= self.tja.offset*1000 + self.start_delay) and not self.song_started:
            if not audio.is_sound_playing(self.song_music):
                audio.play_sound(self.song_music)
            if self.movie is not None:
                self.movie.start(get_current_ms())
            self.song_started = True
        if self.movie is not None:
            self.movie.update()
        else:
            self.background.update(get_current_ms(), self.player_1.gauge.gauge_length > self.player_1.gauge.clear_start[min(self.player_1.difficulty, 3)])

        self.player_1.update(self)
        if self.song_info is not None:
            self.song_info.update(get_current_ms())

        if self.result_transition is not None:
            self.result_transition.update(get_current_ms())
            if self.result_transition.is_finished:
                return self.on_screen_end()
        elif len(self.player_1.play_notes) == 0:
            session_data.result_score, session_data.result_good, session_data.result_ok, session_data.result_bad, session_data.result_max_combo, session_data.result_total_drumroll = self.player_1.get_result_score()
            self.write_score()
            session_data.result_gauge_length = self.player_1.gauge.gauge_length
            if self.end_ms != 0:
                if get_current_ms() >= self.end_ms + 8533.34:
                    self.result_transition = ResultTransition(self.height)
                    audio.play_sound(self.sound_result_transition)
            else:
                self.end_ms = get_current_ms()

    def draw(self):
        if self.movie is not None:
            self.movie.draw()
        else:
            self.background.draw()
        self.player_1.draw(self)
        if self.song_info is not None:
            self.song_info.draw(self)
        if self.result_transition is not None:
            self.result_transition.draw(self.width, self.height, self.result_transition_1, self.result_transition_2)

class Player:
    TIMING_GOOD = 25.0250015258789
    TIMING_OK = 75.0750045776367
    TIMING_BAD = 108.441665649414

    def __init__(self, game_screen: GameScreen, player_number: int, difficulty: int, metadata, judge_offset: int):

        self.player_number = player_number
        self.difficulty = difficulty

        self.play_notes, self.draw_note_list, self.draw_bar_list = game_screen.tja.notes_to_position(self.difficulty)
        self.total_notes = len([note for note in self.play_notes if 0 < note.type < 5])
        self.base_score = calculate_base_score(self.play_notes)

        self.judge_offset = judge_offset

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
        self.base_score_list: list[ScoreCounterAnimation] = []
        self.combo_display = Combo(self.combo, get_current_ms())
        self.score_counter = ScoreCounter(self.score)

        self.input_log: dict[float, tuple] = dict()

        self.gauge = Gauge(self.difficulty, metadata[-1][self.difficulty][0])
        self.gauge_hit_effect: list[GaugeHitEffect] = []

        self.autoplay_hit_side = 'L'

    def get_result_score(self):
        return self.score, self.good_count, self.ok_count, self.bad_count, self.total_drumroll, self.max_combo

    def get_position(self, game_screen: GameScreen, ms: float, pixels_per_frame: float) -> int:
        return int(game_screen.width + pixels_per_frame * 60 / 1000 * (ms - game_screen.current_ms + self.judge_offset) - 64)

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
            position = self.get_position(game_screen, bar.hit_ms, bar.pixels_per_frame)
            if position < game_screen.judge_x + 650:
                self.current_bars.pop(i)

    def play_note_manager(self, game_screen: GameScreen):
        if len(self.play_notes) == 0:
            return

        note = self.play_notes[0]
        if note.hit_ms + Player.TIMING_BAD < game_screen.current_ms:
            if 0 < note.type <= 4:
                self.combo = 0
                self.bad_count += 1
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
            elif note.type == 7:
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
        position = self.get_position(game_screen, note.hit_ms, note.pixels_per_frame)
        if position < game_screen.judge_x + 650:
            self.current_notes_draw.pop(0)

    def note_manager(self, game_screen: GameScreen):
        self.bar_manager(game_screen)
        self.play_note_manager(game_screen)
        self.draw_note_manager(game_screen)

    def note_correct(self, game_screen: GameScreen, note: Note):
        self.play_notes.popleft()
        index = note.index
        if note.type == 7:
            note_type = game_screen.note_type_list[3][0]
            self.play_notes.popleft()
        else:
            note_type = game_screen.note_type_list[note.type][0]

        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        self.draw_arc_list.append(NoteArc(note_type, get_current_ms(), self.player_number, note.type == 3 or note.type == 4) or note.type == 7)
        #game_screen.background.chibis.append(game_screen.background.Chibi())

        if note in self.current_notes_draw:
            index = self.current_notes_draw.index(note)
            self.current_notes_draw.pop(index)

    def check_drumroll(self, game_screen: GameScreen, drum_type: int):
        note_type = game_screen.note_type_list[drum_type][0]
        self.draw_arc_list.append(NoteArc(note_type, get_current_ms(), self.player_number, drum_type == 3 or drum_type == 4))
        self.curr_drumroll_count += 1
        self.total_drumroll += 1
        self.score += 100
        self.base_score_list.append(ScoreCounterAnimation(100))
        if not isinstance(self.current_notes_draw[0], Drumroll):
            return
        self.current_notes_draw[0].color = max(0, 255 - (self.curr_drumroll_count * 10))

    def check_balloon(self, game_screen: GameScreen, drum_type: int, note: Balloon):
        if drum_type != 1:
            return
        if self.balloon_anim is None:
            self.balloon_anim = BalloonAnimation(get_current_ms(), note.count)
        self.curr_balloon_count += 1
        self.total_drumroll += 1
        self.score += 100
        self.base_score_list.append(ScoreCounterAnimation(100))
        if self.curr_balloon_count == note.count:
            self.is_balloon = False
            note.popped = True
            self.balloon_anim.update(game_screen, get_current_ms(), self.curr_balloon_count, note.popped)
            audio.play_sound(game_screen.sound_balloon_pop)
            self.note_correct(game_screen, self.play_notes[0])

    def check_note(self, game_screen: GameScreen, drum_type: int):
        if len(self.play_notes) == 0:
            return

        curr_note = self.play_notes[0]
        if self.is_drumroll:
            self.check_drumroll(game_screen, drum_type)
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
            if (curr_note.hit_ms - Player.TIMING_GOOD) + self.judge_offset <= game_screen.current_ms <= (curr_note.hit_ms + Player.TIMING_GOOD) + self.judge_offset:
                self.draw_judge_list.append(Judgement('GOOD', big))
                self.lane_hit_effect = LaneHitEffect('GOOD')
                self.good_count += 1
                self.score += self.base_score
                self.base_score_list.append(ScoreCounterAnimation(self.base_score))
                self.note_correct(game_screen, curr_note)

            elif (curr_note.hit_ms - Player.TIMING_OK) + self.judge_offset <= game_screen.current_ms <= (curr_note.hit_ms + Player.TIMING_OK) + self.judge_offset:
                self.draw_judge_list.append(Judgement('OK', big))
                self.ok_count += 1
                self.score += 10 * math.floor(self.base_score / 2 / 10)
                self.base_score_list.append(ScoreCounterAnimation(10 * math.floor(self.base_score / 2 / 10)))
                self.note_correct(game_screen, curr_note)

            elif (curr_note.hit_ms - Player.TIMING_BAD) + self.judge_offset <= game_screen.current_ms <= (curr_note.hit_ms + Player.TIMING_BAD) + self.judge_offset:
                self.draw_judge_list.append(Judgement('BAD', big))
                self.bad_count += 1
                self.combo = 0
                self.play_notes.popleft()

    def drumroll_counter_manager(self, game_screen: GameScreen):
        if self.is_drumroll and self.curr_drumroll_count > 0 and self.drumroll_counter is None:
            self.drumroll_counter = DrumrollCounter(get_current_ms())

        if self.drumroll_counter is not None:
            if self.drumroll_counter.is_finished and not self.is_drumroll:
                self.drumroll_counter = None
            else:
                self.drumroll_counter.update(game_screen, get_current_ms(), self.curr_drumroll_count)

    def balloon_manager(self, game_screen: GameScreen):
        if self.balloon_anim is not None:
            self.balloon_anim.update(game_screen, get_current_ms(), self.curr_balloon_count, not self.is_balloon)
            if self.balloon_anim.is_finished:
                self.balloon_anim = None

    def key_manager(self, game_screen: GameScreen):
        key_configs = [
                {"keys": get_config()["keybinds"]["left_don"], "type": "DON", "side": "L", "note_type": 1},
                {"keys": get_config()["keybinds"]["right_don"], "type": "DON", "side": "R", "note_type": 1},
                {"keys": get_config()["keybinds"]["left_kat"], "type": "KAT", "side": "L", "note_type": 2},
                {"keys": get_config()["keybinds"]["right_kat"], "type": "KAT", "side": "R", "note_type": 2}
            ]
        for config in key_configs:
            for key in config["keys"]:
                if ray.is_key_pressed(ord(key)):
                    hit_type = config["type"]
                    self.lane_hit_effect = LaneHitEffect(hit_type)
                    self.draw_drum_hit_list.append(DrumHitEffect(hit_type, config["side"]))

                    sound = game_screen.sound_don if hit_type == "DON" else game_screen.sound_kat
                    audio.play_sound(sound)

                    self.check_note(game_screen, config["note_type"])
                    self.input_log[game_screen.current_ms] = (hit_type, key)

    def autoplay_manager(self, game_screen):
        if not get_config()["general"]["autoplay"]:
            return
        if len(self.play_notes) == 0:
            return
        note = self.play_notes[0]
        if game_screen.current_ms >= note.hit_ms and note.type != 8:
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


    def update(self, game_screen: GameScreen):
        self.note_manager(game_screen)
        self.combo_display.update(game_screen, get_current_ms(), self.combo)
        self.drumroll_counter_manager(game_screen)
        self.animation_manager(self.draw_judge_list)
        self.balloon_manager(game_screen)
        if self.lane_hit_effect is not None:
            self.lane_hit_effect.update(get_current_ms())
        self.animation_manager(self.draw_drum_hit_list)
        for anim in self.draw_arc_list:
            anim.update(get_current_ms())
            if anim.is_finished:
                self.gauge_hit_effect.append(GaugeHitEffect(anim.texture, anim.is_big))
                self.draw_arc_list.remove(anim)
        self.animation_manager(self.gauge_hit_effect)
        self.animation_manager(self.base_score_list)
        self.score_counter.update(get_current_ms(), self.score)
        self.autoplay_manager(game_screen)
        self.key_manager(game_screen)

        self.gauge.update(get_current_ms(), self.good_count, self.ok_count, self.bad_count, self.total_notes)

    def draw_drumroll(self, game_screen: GameScreen, head: Drumroll, current_eighth: int):
        start_position = self.get_position(game_screen, head.load_ms, head.pixels_per_frame)
        tail = next((note for note in self.current_notes_draw[1:] if note.type == 8 and note.index > head.index), None)
        if tail is None:
            raise Exception("Tail for Balloon not found")
        is_big = int(head.type == 6) * 2
        end_position = self.get_position(game_screen, tail.load_ms, tail.pixels_per_frame)
        length = (end_position - start_position - 50)
        if length <= 0:
            end_position += 50
        source_rect = ray.Rectangle(0,0,game_screen.note_type_list[8].width, game_screen.note_type_list[8].height)
        dest_rect = ray.Rectangle(start_position+64, 192, length, game_screen.note_type_list[1][0].height)
        color = ray.Color(255, head.color, head.color, 255)
        ray.draw_texture_pro(game_screen.note_type_list[8 + is_big], source_rect, dest_rect, ray.Vector2(0,0), 0, color)
        ray.draw_texture(game_screen.note_type_list[9 + is_big], end_position, 192, color)
        ray.draw_texture(game_screen.note_type_list[head.type][current_eighth % 2], start_position, 192, color)

        source_rect = ray.Rectangle(0,0,game_screen.texture_se_moji[8].width,game_screen.texture_se_moji[8].height)
        dest_rect = ray.Rectangle(start_position - (game_screen.texture_se_moji[8].width // 2) + 64, 323, length,game_screen.texture_se_moji[8].height)
        ray.draw_texture_pro(game_screen.texture_se_moji[8], source_rect, dest_rect, ray.Vector2(0,0), 0, ray.WHITE)
        moji_texture = game_screen.texture_se_moji[head.moji]
        ray.draw_texture(moji_texture, start_position - (moji_texture.width//2) + 64, 323, ray.WHITE)
        moji_texture = game_screen.texture_se_moji[tail.moji]
        ray.draw_texture(moji_texture, (end_position - (moji_texture.width//2)) + 32, 323, ray.WHITE)

    def draw_balloon(self, game_screen: GameScreen, head: Balloon, current_eighth: int):
        offset = 12
        start_position = self.get_position(game_screen, head.load_ms, head.pixels_per_frame)
        tail = next((note for note in self.current_notes_draw[1:] if note.type == 8 and note.index > head.index), None)
        if tail is None:
            raise Exception("Tail for Balloon not found")
        end_position = self.get_position(game_screen, tail.load_ms, tail.pixels_per_frame)
        pause_position = 349
        if game_screen.current_ms >= tail.hit_ms:
            position = end_position
        elif game_screen.current_ms >= head.hit_ms:
            position = pause_position
        else:
            position = start_position
        ray.draw_texture(game_screen.note_type_list[head.type][current_eighth % 2], position-offset, 192, ray.WHITE)
        ray.draw_texture(game_screen.note_type_list[12], position-offset+128, 192, ray.WHITE)

    def draw_bars(self, game_screen: GameScreen):
        if len(self.current_bars) <= 0:
            return

        for bar in reversed(self.current_bars):
            position = self.get_position(game_screen, bar.load_ms, bar.pixels_per_frame)
            ray.draw_texture(game_screen.note_type_list[bar.type], position+60, 190, ray.WHITE)

    def draw_notes(self, game_screen: GameScreen):
        if len(self.current_notes_draw) <= 0:
            return

        eighth_in_ms = (60000 * 4 / game_screen.tja.bpm) / 8
        current_eighth = 0
        if self.combo >= 50:
            current_eighth = int((game_screen.current_ms - game_screen.start_ms) // eighth_in_ms)

        for note in reversed(self.current_notes_draw):
            if self.is_balloon and note == self.current_notes_draw[0]:
                continue
            if note.type == 8:
                continue
            position = self.get_position(game_screen, note.load_ms, note.pixels_per_frame)
            if isinstance(note, Drumroll):
                self.draw_drumroll(game_screen, note, current_eighth)
            elif isinstance(note, Balloon):
                self.draw_balloon(game_screen, note, current_eighth)
                moji_texture = game_screen.texture_se_moji[note.moji]
                ray.draw_texture(moji_texture, position - (moji_texture.width//2) + 64, 323, ray.WHITE)
            else:
                ray.draw_texture(game_screen.note_type_list[note.type][current_eighth % 2], position, 192, ray.WHITE)
                moji_texture = game_screen.texture_se_moji[note.moji]
                ray.draw_texture(moji_texture, position - (moji_texture.width//2) + 64, 323, ray.WHITE)
            #ray.draw_text(str(note.index), position+64, 192, 25, ray.GREEN)

    def draw(self, game_screen: GameScreen):
        ray.draw_texture(game_screen.textures['lane'][0], 332, 184, ray.WHITE)
        self.gauge.draw(game_screen.textures['gage_don_1p_hard'])
        if self.lane_hit_effect is not None:
            self.lane_hit_effect.draw(game_screen.textures['lane_hit'])
        ray.draw_texture(game_screen.textures['lane_hit'][17], 342, 184, ray.WHITE)
        for anim in self.draw_judge_list:
            anim.draw(game_screen.textures['lane_hit'], game_screen.textures['lane_hit_effect'])

        #ray.draw_texture(game_screen.textures['onp_kiseki_don_1p'][0], 350, 192, ray.WHITE)
        #ray.draw_texture(game_screen.textures['onp_kiseki_don_1p'][22], 332, -84, ray.WHITE)
        #ray.draw_texture(game_screen.textures['onp_kiseki_don_1p'][6], 1187 - 29, 130 - 29, ray.WHITE)

        self.draw_bars(game_screen)
        self.draw_notes(game_screen)
        ray.draw_texture(game_screen.textures['lane_obi'][0], 0, 184, ray.WHITE)
        ray.draw_texture(game_screen.textures['lane_obi'][14], 211, 206, ray.WHITE)
        if get_config()["general"]["autoplay"]:
            ray.draw_texture(game_screen.textures['lane_obi'][58], 0, 290, ray.WHITE)
        for anim in self.draw_drum_hit_list:
            anim.draw(game_screen)
        self.combo_display.draw(game_screen)
        ray.draw_texture(game_screen.textures['lane_obi'][3], 0, 184, ray.WHITE)
        ray.draw_texture(game_screen.textures['lane_obi'][19], 0, 225, ray.WHITE)
        ray.draw_texture(game_screen.textures['lane_obi'][self.difficulty+21], 50, 222, ray.WHITE)
        if self.drumroll_counter is not None:
            self.drumroll_counter.draw(game_screen)
        for anim in self.draw_arc_list:
            anim.draw(game_screen)
        for anim in self.gauge_hit_effect:
            anim.draw(game_screen)
        if self.balloon_anim is not None:
            self.balloon_anim.draw(game_screen)
        self.score_counter.draw(game_screen)
        for anim in self.base_score_list:
            anim.draw(game_screen)

class Judgement:
    def __init__(self, type: str, big: bool):
        self.type = type
        self.big = big
        self.is_finished = False

        self.fade_animation_1 = Animation.create_fade(132, initial_opacity=0.5, delay=100)
        self.fade_animation_2 = Animation.create_fade(316 - 233.3, delay=233.3)
        self.move_animation = Animation.create_move(83, total_distance=15, start_position=144)
        self.texture_animation = Animation.create_texture_change(100, textures=[(33, 50, 1), (50, 83, 2), (83, 100, 3), (100, float('inf'), 4)])

    def update(self, current_ms):
        self.fade_animation_1.update(current_ms)
        self.fade_animation_2.update(current_ms)
        self.move_animation.update(current_ms)
        self.texture_animation.update(current_ms)

        if self.fade_animation_2.is_finished:
            self.is_finished = True

    def draw(self, textures_1: list[ray.Texture], textures_2: list[ray.Texture]):
        y = self.move_animation.attribute
        index = int(self.texture_animation.attribute)
        hit_color = ray.fade(ray.WHITE, self.fade_animation_1.attribute)
        color = ray.fade(ray.WHITE, self.fade_animation_2.attribute)
        if self.type == 'GOOD':
            if self.big:
                ray.draw_texture(textures_1[21], 342, 184, color)
                ray.draw_texture(textures_2[index+11], 304, 143, hit_color)
            else:
                ray.draw_texture(textures_1[19], 342, 184, color)
                ray.draw_texture(textures_2[index+5], 304, 143, hit_color)
            ray.draw_texture(textures_2[9], 370, int(y), color)
        elif self.type == 'OK':
            if self.big:
                ray.draw_texture(textures_1[20], 342, 184, color)
                ray.draw_texture(textures_2[index+16], 304, 143, hit_color)
            else:
                ray.draw_texture(textures_1[18], 342, 184, color)
                ray.draw_texture(textures_2[index], 304, 143, hit_color)
            ray.draw_texture(textures_2[4], 370, int(y), color)
        elif self.type == 'BAD':
            ray.draw_texture(textures_2[10], 370, int(y), color)

class LaneHitEffect:
    def __init__(self, type: str):
        self.type = type
        self.color = ray.fade(ray.WHITE, 0.5)
        self.fade = Animation.create_fade(150, delay=83, initial_opacity=0.5)
        self.is_finished = False

    def update(self, current_ms: float):
        self.fade.update(current_ms)
        fade_opacity = self.fade.attribute
        self.color = ray.fade(ray.WHITE, fade_opacity)
        if self.fade.is_finished:
            self.is_finished = True

    def draw(self, textures: list[ray.Texture]):
        if self.type == 'GOOD':
            ray.draw_texture(textures[7], 328, 192, self.color)
        elif self.type == 'DON':
            ray.draw_texture(textures[5], 328, 192, self.color)
        elif self.type == 'KAT':
            ray.draw_texture(textures[6], 328, 192, self.color)

class DrumHitEffect:
    def __init__(self, type: str, side: str):
        self.type = type
        self.side = side
        self.color = ray.fade(ray.WHITE, 1)
        self.is_finished = False
        self.fade = Animation.create_fade(100, delay=67)

    def update(self, current_ms: float):
        self.fade.update(current_ms)
        fade_opacity = self.fade.attribute
        self.color = ray.fade(ray.WHITE, fade_opacity)
        if self.fade.is_finished:
            self.is_finished = True

    def draw(self, game_screen):
        x, y = 211, 206
        if self.type == 'DON':
            if self.side == 'L':
                ray.draw_texture(game_screen.textures['lane_obi'][16], x, y, self.color)
            elif self.side == 'R':
                ray.draw_texture(game_screen.textures['lane_obi'][15], x, y, self.color)
        elif self.type == 'KAT':
            if self.side == 'L':
                ray.draw_texture(game_screen.textures['lane_obi'][18], x, y, self.color)
            elif self.side == 'R':
                ray.draw_texture(game_screen.textures['lane_obi'][17], x, y, self.color)

class GaugeHitEffect:
    def __init__(self, note_texture: ray.Texture, big: bool):
        self.note_texture = note_texture
        self.is_big = big
        self.texture_change = Animation.create_texture_change(116.67, textures=[(0, 33.33, 1), (33.33, 66.66, 2), (66.66, float('inf'), 3)])
        self.circle_fadein = Animation.create_fade(133, initial_opacity=0.0, final_opacity=1.0, delay=16.67)
        self.resize = Animation.create_texture_resize(233, delay=self.texture_change.duration, initial_size=0.75, final_size=1.15)
        self.fade_out = Animation.create_fade(66, delay=233)
        self.test = Animation.create_fade(300, delay=116.67, initial_opacity=0.0, final_opacity=1.0)
        self.color = ray.fade(ray.YELLOW, self.circle_fadein.attribute)
        self.is_finished = False
    def update(self, current_ms):
        self.texture_change.update(current_ms)
        self.circle_fadein.update(current_ms)
        self.fade_out.update(current_ms)
        self.resize.update(current_ms)
        self.test.update(current_ms)
        color = ray.YELLOW
        if self.circle_fadein.is_finished:
            color = ray.WHITE
        self.color = ray.fade(color, min(self.fade_out.attribute, self.circle_fadein.attribute))
        if self.fade_out.is_finished:
            self.is_finished = True
    def draw(self, game_screen):
        texture = game_screen.textures['onp_kiseki_don_1p'][self.texture_change.attribute]
        color_map = {0.70: ray.WHITE, 0.80: ray.YELLOW, 0.90: ray.ORANGE, 1.00: ray.RED}
        texture_color = ray.WHITE
        for upper_bound, color in color_map.items():
            lower_bound = list(color_map.keys())[list(color_map.keys()).index(upper_bound) - 1] if list(color_map.keys()).index(upper_bound) > 0 else 0.70

            if lower_bound <= self.resize.attribute <= upper_bound:
                texture_color = color
            elif self.resize.attribute >= upper_bound:
                texture_color = ray.RED
        original_x = 1223
        original_y = 164
        source = ray.Rectangle(0, 0, texture.width, texture.height)
        dest_width = texture.width * self.resize.attribute
        dest_height = texture.height * self.resize.attribute
        dest = ray.Rectangle(original_x, original_y, dest_width, dest_height)
        origin = ray.Vector2(dest_width / 2, dest_height / 2)
        ray.draw_texture_pro(texture, source, dest, origin, self.test.attribute*100, ray.fade(texture_color, self.fade_out.attribute))
        ray.draw_texture(self.note_texture, 1187 - 29, 130 - 29, ray.fade(ray.WHITE, self.fade_out.attribute))
        if self.is_big:
            ray.draw_texture(game_screen.textures['onp_kiseki_don_1p'][20], 1187 - 29, 130 - 29, self.color)
        else:
            ray.draw_texture(game_screen.textures['onp_kiseki_don_1p'][4], 1187 - 29, 130 - 29, self.color)

class NoteArc:
    def __init__(self, note_texture: ray.Texture, current_ms: float, player_number: int, big: bool):
        self.texture = note_texture
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

    def draw(self, game_screen):
        ray.draw_texture(self.texture, self.x_i, self.y_i, ray.WHITE)

class DrumrollCounter:
    def __init__(self, current_ms: float):
        self.create_ms = current_ms
        self.is_finished = False
        self.total_duration = 1349
        self.drumroll_count = 0
        self.fade_animation = Animation.create_fade(166, delay=self.total_duration - 166)
        self.stretch_animation = Animation.create_text_stretch(0)

    def update_count(self, count: int, elapsed_time: float):
        self.total_duration = elapsed_time + 1349
        self.fade_animation.delay = self.total_duration - 166
        if self.drumroll_count != count:
            self.drumroll_count = count
            self.stretch_animation = Animation.create_text_stretch(50)

    def update(self, game_screen: GameScreen, current_ms: float, drumroll_count: int):
        self.stretch_animation.update(current_ms)
        self.fade_animation.update(current_ms)

        elapsed_time = current_ms - self.create_ms
        if drumroll_count != 0:
            self.update_count(drumroll_count, elapsed_time)
        if self.fade_animation.is_finished:
            self.is_finished = True

    def draw(self, game_screen: GameScreen):
        color = ray.fade(ray.WHITE, self.fade_animation.attribute)
        ray.draw_texture(game_screen.textures['renda_num'][0], 200, 0, color)
        counter = str(self.drumroll_count)
        total_width = len(counter) * 52
        start_x = 344 - (total_width // 2)
        source_rect = ray.Rectangle(0, 0, game_screen.textures['renda_num'][1].width, game_screen.textures['renda_num'][1].height)
        for i in range(len(counter)):
            dest_rect = ray.Rectangle(start_x + (i * 52), 50 - self.stretch_animation.attribute, game_screen.textures['renda_num'][1].width, game_screen.textures['renda_num'][1].height + self.stretch_animation.attribute)
            ray.draw_texture_pro(game_screen.textures['renda_num'][int(counter[i])+1], source_rect, dest_rect, ray.Vector2(0,0), 0, color)

class BalloonAnimation:
    def __init__(self, current_ms: float, balloon_total: int):
        self.create_ms = current_ms
        self.is_finished = False
        self.total_duration = 83.33
        self.color = ray.fade(ray.WHITE, 1.0)
        self.balloon_count = 0
        self.balloon_total = balloon_total
        self.is_popped = False
        self.fade_animation = Animation.create_fade(166)
        self.stretch_animation = Animation.create_text_stretch(0)

    def update_count(self, balloon_count: int):
        if self.balloon_count != balloon_count:
            self.balloon_count = balloon_count
            self.stretch_animation = Animation.create_text_stretch(50)

    def update(self, game_screen: GameScreen, current_ms: float, balloon_count: int, is_popped: bool):
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

    def draw(self, game_screen: GameScreen):
        if self.is_popped:
            ray.draw_texture(game_screen.textures['action_fusen_1p'][18], 460, 130, self.color)
        elif self.balloon_count >= 1:
            balloon_index = min(7, (self.balloon_count - 1) * 7 // self.balloon_total)
            ray.draw_texture(game_screen.textures['action_fusen_1p'][balloon_index+11], 460, 130, self.color)
        if self.balloon_count > 0:
            ray.draw_texture(game_screen.textures['action_fusen_1p'][0], 414, 40, ray.WHITE)
            counter = str(max(0, self.balloon_total - self.balloon_count + 1))
            x, y = 493, 68
            margin = 52
            total_width = len(counter) * margin
            start_x = x - (total_width // 2)
            source_rect = ray.Rectangle(0, 0, game_screen.textures['action_fusen_1p'][1].width, game_screen.textures['action_fusen_1p'][1].height)
            for i in range(len(counter)):
                dest_rect = ray.Rectangle(start_x + (i * margin), y - self.stretch_animation.attribute, game_screen.textures['action_fusen_1p'][1].width, game_screen.textures['action_fusen_1p'][1].height + self.stretch_animation.attribute)
                ray.draw_texture_pro(game_screen.textures['action_fusen_1p'][int(counter[i])+1], source_rect, dest_rect, ray.Vector2(0,0), 0, self.color)

class Combo:
    def __init__(self, combo: int, current_ms: float):
        self.combo = combo
        self.stretch_animation = Animation.create_text_stretch(0)
        self.color = [ray.fade(ray.WHITE, 1), ray.fade(ray.WHITE, 1), ray.fade(ray.WHITE, 1)]
        self.glimmer_dict = {0: 0, 1: 0, 2: 0}
        self.total_time = 250
        self.cycle_time = self.total_time * 2
        self.start_times = [
                    current_ms,
                    current_ms + (2 / 3) * self.cycle_time,
                    current_ms + (4 / 3) * self.cycle_time
                ]

    def update_count(self, current_ms: float, combo: int):
        if self.combo != combo:
            self.combo = combo
            self.stretch_animation = Animation.create_text_stretch(50)

    def update(self, game_screen: GameScreen, current_ms: float, combo: int):
        self.update_count(current_ms, combo)
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

    def draw(self, game_screen: GameScreen):
        if self.combo < 3:
            return
        if self.combo < 100:
            text_color = 0
            margin = 30
        else:
            text_color = 1
            margin = 35
        ray.draw_texture(game_screen.texture_combo_text[text_color], 234, 265, ray.WHITE)
        counter = str(self.combo)
        total_width = len(counter) * margin
        x, y = 262, 220
        start_x = x - (total_width // 2)
        source_rect = ray.Rectangle(0, 0, game_screen.texture_combo_numbers[0].width, game_screen.texture_combo_numbers[0].height)
        for i in range(len(counter)):
            dest_rect = ray.Rectangle(start_x + (i * margin), y - self.stretch_animation.attribute, game_screen.texture_combo_numbers[0].width, game_screen.texture_combo_numbers[0].height + self.stretch_animation.attribute)
            ray.draw_texture_pro(game_screen.texture_combo_numbers[int(counter[i]) + (text_color*10)], source_rect, dest_rect, ray.Vector2(0,0), 0, ray.WHITE)
        glimmer_positions = [(225, 210), (200, 230), (250, 230)]
        if self.combo >= 100:
            for j, (x, y) in enumerate(glimmer_positions):
                for i in range(3):
                    ray.draw_texture(game_screen.texture_combo_glimmer, x + (i * 30), y + self.glimmer_dict[j], self.color[j])

class ScoreCounter:
    def __init__(self, score: int):
        self.score = score
        self.stretch_animation = Animation.create_text_stretch(0)

    def update_count(self, current_ms: float, score: int):
        if self.score != score:
            self.score = score
            self.stretch_animation = Animation.create_text_stretch(50)

    def update(self, current_ms: float, score: int):
        self.update_count(current_ms, score)
        if self.score > 0:
            self.stretch_animation.update(current_ms)

    def draw(self, game_screen: GameScreen):
        counter = str(self.score)
        x, y = 150, 185
        margin = 20
        total_width = len(counter) * margin
        start_x = x - total_width
        source_rect = ray.Rectangle(0, 0, game_screen.textures['lane_obi'][4].width, game_screen.textures['lane_obi'][4].height)
        for i in range(len(counter)):
            dest_rect = ray.Rectangle(start_x + (i * margin), y - self.stretch_animation.attribute, game_screen.textures['lane_obi'][4].width, game_screen.textures['lane_obi'][4].height + self.stretch_animation.attribute)
            ray.draw_texture_pro(game_screen.textures['lane_obi'][int(counter[i])+4], source_rect, dest_rect, ray.Vector2(0,0), 0, ray.WHITE)

class ScoreCounterAnimation:
    def __init__(self, counter: int):
        self.counter = counter
        self.fade_animation_1 = Animation.create_fade(50, initial_opacity=0.0, final_opacity=1.0)
        self.move_animation_1 = Animation.create_move(80, total_distance=-20, start_position=175)
        self.fade_animation_2 = Animation.create_fade(80, delay=366.74)
        self.move_animation_2 = Animation.create_move(66, total_distance=5, start_position=145, delay=80)
        self.move_animation_3 = Animation.create_move(66, delay=279.36, total_distance=-2, start_position=146)
        self.move_animation_4 = Animation.create_move(80, delay=366.74, total_distance=10, start_position=148)

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
            self.color = ray.fade(ray.Color(254, 102, 0, 255), self.fade_animation_2.attribute)
        else:
            self.color = ray.fade(ray.Color(254, 102, 0, 255), self.fade_animation_1.attribute)
        if self.fade_animation_2.is_finished:
            self.is_finished = True
        self.y_pos_list = []
        for i in range(1, len(str(self.counter))+1):
            self.y_pos_list.append(self.move_animation_4.attribute + i*5)

    def draw(self, game_screen: GameScreen):
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
        source_rect = ray.Rectangle(0, 0, game_screen.textures['score_add_1p'][0].width, game_screen.textures['score_add_1p'][0].height)
        for i in range(len(counter)):
            if self.move_animation_3.is_finished:
                y = self.y_pos_list[i]
            elif self.move_animation_2.is_finished:
                y = self.move_animation_3.attribute
            else:
                y = 148
            dest_rect = ray.Rectangle(start_x + (i * margin), y, game_screen.textures['score_add_1p'][0].width, game_screen.textures['score_add_1p'][0].height)
            ray.draw_texture_pro(game_screen.textures['score_add_1p'][int(counter[i])], source_rect, dest_rect, ray.Vector2(0,0), 0, self.color)

class SongInfo:
    FADE_DURATION = 366
    DISPLAY_DURATION = 1666

    def __init__(self, song_name: str, genre: str):
        self.song_name = song_name
        self.genre = genre

        self.font = self._load_font_for_text(song_name)
        self.song_title = OutlinedText(
            self.font, song_name, 40, ray.WHITE, ray.BLACK, outline_thickness=4
        )
        self.fade_in = Animation.create_fade(self.FADE_DURATION, initial_opacity=0.0, final_opacity=1.0)
        self.fade_out = Animation.create_fade(self.FADE_DURATION, delay=self.DISPLAY_DURATION)
        self.fade_fake = Animation.create_fade(0, delay=self.DISPLAY_DURATION*2 + self.FADE_DURATION)

    def _load_font_for_text(self, text: str) -> ray.Font:
        codepoint_count = ray.ffi.new('int *', 0)
        unique_codepoints = set(text)
        codepoints = ray.load_codepoints(''.join(unique_codepoints), codepoint_count)
        return ray.load_font_ex(str(Path('Graphics/Modified-DFPKanteiryu-XB.ttf')), 32, codepoints, 0)

    def update(self, current_ms: float):
        self.fade_in.update(current_ms)
        self.fade_out.update(current_ms)
        self.fade_fake.update(current_ms)

        if not self.fade_in.is_finished:
            self.song_num_fade = ray.fade(ray.WHITE, self.fade_in.attribute)
            self.song_name_fade = ray.fade(ray.WHITE, 1 - self.fade_in.attribute)
        else:
            self.song_num_fade = ray.fade(ray.WHITE, self.fade_out.attribute)
            self.song_name_fade = ray.fade(ray.WHITE, 1 - self.fade_out.attribute)

        if self.fade_fake.is_finished:
            self._reset_animations(current_ms)

    def _reset_animations(self, current_ms: float):
        self.fade_in = Animation.create_fade(self.FADE_DURATION, initial_opacity=0.0, final_opacity=1.0)
        self.fade_out = Animation.create_fade(self.FADE_DURATION, delay=self.DISPLAY_DURATION)
        self.fade_fake = Animation.create_fade(0, delay=self.DISPLAY_DURATION*2 + self.FADE_DURATION)

    def draw(self, game_screen: GameScreen):
        song_texture_index = (global_data.songs_played % 4) + 8
        ray.draw_texture(
            game_screen.textures['song_info'][song_texture_index],
            1132, 25,
            self.song_num_fade
        )

        text_x = 1252 - self.song_title.texture.width
        text_y = int(50 - self.song_title.texture.height / 2)
        src = ray.Rectangle(0, 0, self.song_title.texture.width, self.song_title.texture.height)
        dest = ray.Rectangle(text_x, text_y, self.song_title.texture.width, self.song_title.texture.height)
        self.song_title.draw(src, dest, ray.Vector2(0, 0), 0, self.song_name_fade)

class ResultTransition:
    def __init__(self, screen_height: int):
        self.move = Animation.create_move(983.33, start_position=0, total_distance=screen_height//2, ease_out='quadratic')

        self.is_finished = False

    def update(self, current_ms: float):
        self.move.update(current_ms)

        if self.move.is_finished:
            self.is_finished = True

    def draw(self, screen_width: int, screen_height: int, texture_1: ray.Texture, texture_2: ray.Texture):
        x = 0
        while x < screen_width:
            ray.draw_texture(texture_1, x, (0 - texture_1.height) + int(self.move.attribute), ray.WHITE)
            ray.draw_texture(texture_1, x, (screen_height) - int(self.move.attribute), ray.WHITE)
            x += texture_1.width
        x = 0
        while x < screen_width:
            ray.draw_texture(texture_2, x, (0 - texture_2.height//2) - (texture_1.height//2) + int(self.move.attribute), ray.WHITE)
            ray.draw_texture(texture_2, x, (screen_height) + (texture_1.height//2) - (texture_2.height//2) - int(self.move.attribute), ray.WHITE)
            x += texture_2.width

class Gauge:
    def __init__(self, difficulty: int, level: int):
        self.gauge_length = 0
        self.difficulty = min(3, difficulty)
        self.clear_start = [0, 0, 68, 68]
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
        self.gauge_update_anim = None
        self.rainbow_fade_in = None
        self.rainbow_animation = None

    def update(self, current_ms: float, good_count: int, ok_count: int, bad_count: int, total_notes: int):
        gauge_length = int(((good_count +
            (ok_count * self.table[self.difficulty][self.level]["ok_multiplier"] +
            bad_count * self.table[self.difficulty][self.level]["bad_multiplier"])) / total_notes) * (100 * (self.clear_start[self.difficulty] / self.table[self.difficulty][self.level]["clear_rate"])))
        previous_length = self.gauge_length
        self.gauge_length = min(87, gauge_length)
        if self.gauge_length == 87 and self.rainbow_fade_in is None:
            self.rainbow_fade_in = Animation.create_fade(450, initial_opacity=0.0, final_opacity=1.0)
        if self.gauge_length > previous_length:
            self.gauge_update_anim = Animation.create_fade(450)

        if self.gauge_update_anim is not None:
            self.gauge_update_anim.update(current_ms)
            if self.gauge_update_anim.is_finished:
                self.gauge_update_anim = None

        if self.rainbow_fade_in is not None:
            self.rainbow_fade_in.update(current_ms)

        if self.rainbow_animation is None:
            self.rainbow_animation = Animation.create_texture_change((16.67*8) * 3, textures=[((16.67 * 3) * i, (16.67 * 3) * (i + 1), i) for i in range(8)])
        else:
            self.rainbow_animation.update(current_ms)
            if self.rainbow_animation.is_finished or self.gauge_length < 87:
                self.rainbow_animation = None

    def draw(self, textures: list[ray.Texture]):
        ray.draw_texture(textures[0], 327, 132, ray.WHITE)
        ray.draw_texture(textures[1], 483, 124, ray.WHITE)
        if self.gauge_length == 87 and self.rainbow_fade_in is not None and self.rainbow_animation is not None:
            if 0 < self.rainbow_animation.attribute < 8:
                ray.draw_texture(textures[1 + int(self.rainbow_animation.attribute)], 483, 124, ray.fade(ray.WHITE, self.rainbow_fade_in.attribute))
            ray.draw_texture(textures[2 + int(self.rainbow_animation.attribute)], 483, 124, ray.fade(ray.WHITE, self.rainbow_fade_in.attribute))
        if self.rainbow_fade_in is None or not self.rainbow_fade_in.is_finished:
            for i in range(self.gauge_length):
                if i == 68:
                    ray.draw_texture(textures[16], 491 + (i*textures[13].width), 160 - 24, ray.WHITE)
                elif i > 68:
                    ray.draw_texture(textures[15], 491 + (i*textures[13].width) + 2, 160 - 22, ray.WHITE)
                    ray.draw_texture(textures[20], 491 + (i*textures[13].width) + 2, 160, ray.WHITE)
                else:
                    ray.draw_texture(textures[13], 491 + (i*textures[13].width), 160, ray.WHITE)
        if self.gauge_update_anim is not None and self.gauge_length < 88:
            if self.gauge_length == 69:
                ray.draw_texture(textures[17], 491 + (self.gauge_length*textures[13].width) - 13, 160 - 8 - 24, ray.fade(ray.WHITE, self.gauge_update_anim.attribute))
            elif self.gauge_length > 69:
                ray.draw_texture(textures[21], 491 + (self.gauge_length*textures[13].width) - 13, 160 - 8 - 22, ray.fade(ray.WHITE, self.gauge_update_anim.attribute))
            else:
                ray.draw_texture(textures[14], 491 + (self.gauge_length*textures[13].width) - 13, 160 - 8, ray.fade(ray.WHITE, self.gauge_update_anim.attribute))
        ray.draw_texture(textures[10], 483, 124, ray.fade(ray.WHITE, 0.15))
        if self.gauge_length >= 69:
            ray.draw_texture(textures[18], 1038, 141, ray.WHITE)
            ray.draw_texture(textures[19], 1187, 130, ray.WHITE)
        else:
            ray.draw_texture(textures[11], 1038, 141, ray.WHITE)
            ray.draw_texture(textures[12], 1187, 130, ray.WHITE)
