import bisect
import hashlib
import math
import logging
import random
from collections import deque
from dataclasses import dataclass, field, fields
from functools import lru_cache
from pathlib import Path

from libs.global_data import Modifiers
from libs.utils import get_pixels_per_frame, strip_comments


@lru_cache(maxsize=64)
def get_ms_per_measure(bpm_val: float, time_sig: float):
    """Calculate the number of milliseconds per measure."""
    #https://gist.github.com/KatieFrogs/e000f406bbc70a12f3c34a07303eec8b#measure
    if bpm_val == 0:
        return 0
    return 60000 * (time_sig * 4) / bpm_val

@lru_cache(maxsize=64)
def get_pixels_per_ms(pixels_per_frame: float):
    """Calculate the number of pixels per millisecond."""
    return pixels_per_frame / (1000 / 60)

@dataclass()
class Note:
    """A note in a TJA file.

    Attributes:
        type (int): The type (color) of the note.
        hit_ms (float): The time at which the note should be hit.
        load_ms (float): The time at which the note should be loaded.
        pixels_per_frame_x (float): The number of pixels per frame in the x direction.
        pixels_per_frame_y (float): The number of pixels per frame in the y direction.
        display (bool): Whether the note should be displayed.
        index (int): The index of the note.
        bpm (float): The beats per minute of the song.
        gogo_time (bool): Whether the note is a gogo time note.
        moji (int): The text drawn below the note.
        is_branch_start (bool): Whether the note is the start of a branch.
        branch_params (str): The parameters (requirements) of the branch.
    """
    type: int = field(init=False)
    hit_ms: float = field(init=False)
    load_ms: float = field(init=False)
    pixels_per_frame_x: float = field(init=False)
    pixels_per_frame_y: float = field(init=False)
    display: bool = field(init=False)
    index: int = field(init=False)
    bpm: float = field(init=False)
    gogo_time: bool = field(init=False)
    moji: int = field(init=False)
    is_branch_start: bool = field(init=False)
    branch_params: str = field(init=False)

    def __lt__(self, other):
        return self.hit_ms < other.hit_ms

    def __le__(self, other):
        return self.hit_ms <= other.hit_ms

    def __gt__(self, other):
        return self.hit_ms > other.hit_ms

    def __ge__(self, other):
        return self.hit_ms >= other.hit_ms

    def __eq__(self, other):
        return self.hit_ms == other.hit_ms

    def _get_hash_data(self) -> bytes:
        hash_fields = ['type', 'hit_ms', 'load_ms']
        field_values = []

        for field_name in sorted(hash_fields):
            value = getattr(self, field_name, None)
            field_values.append((field_name, value))

        field_values.append(('__class__', self.__class__.__name__))
        hash_string = str(field_values)
        return hash_string.encode('utf-8')

    def get_hash(self, algorithm='sha256') -> str:
        """Generate hash of the note"""
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(self._get_hash_data())
        return hash_obj.hexdigest()

    def __hash__(self) -> int:
        """Make instances hashable for use in sets/dicts"""
        return int(self.get_hash('md5')[:8], 16)  # Use first 8 chars of MD5 as int

    def __repr__(self):
        return str(self.__dict__)

@dataclass
class Drumroll(Note):
    """A drumroll note in a TJA file.

    Attributes:
        _source_note (Note): The source note.
        color (int): The color of the drumroll. (0-255 where 255 is red)
    """
    _source_note: Note
    color: int = field(init=False)

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.hit_ms == other.hit_ms

    def __post_init__(self):
        for field_name in [f.name for f in fields(Note)]:
            if hasattr(self._source_note, field_name):
                setattr(self, field_name, getattr(self._source_note, field_name))

@dataclass
class Balloon(Note):
    """A balloon note in a TJA file.

    Attributes:
        _source_note (Note): The source note.
        count (int): The number of hits it takes to pop.
        popped (bool): Whether the balloon has been popped.
        is_kusudama (bool): Whether the balloon is a kusudama.
    """
    _source_note: Note
    count: int = field(init=False)
    popped: bool = False
    is_kusudama: bool = False

    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.hit_ms == other.hit_ms

    def __post_init__(self):
        for field_name in [f.name for f in fields(Note)]:
            if hasattr(self._source_note, field_name):
                setattr(self, field_name, getattr(self._source_note, field_name))

    def _get_hash_data(self) -> bytes:
        """Override to include source note and balloon-specific data"""
        hash_fields = ['type', 'hit_ms', 'load_ms', 'count']
        field_values = []

        for field_name in sorted(hash_fields):
            value = getattr(self, field_name, None)
            field_values.append((field_name, value))

        field_values.append(('__class__', self.__class__.__name__))
        hash_string = str(field_values)
        return hash_string.encode('utf-8')

@dataclass
class NoteList:
    """A collection of notes
    play_notes: A list of notes, drumrolls, and balloons that are played by the player
    draw_notes: A list of notes, drumrolls, and balloons that are drawn by the player
    bars: A list of bars"""
    play_notes: list[Note | Drumroll | Balloon] = field(default_factory=lambda: [])
    draw_notes: list[Note | Drumroll | Balloon] = field(default_factory=lambda: [])
    bars: list[Note] = field(default_factory=lambda: [])

    def __add__(self, other: 'NoteList') -> 'NoteList':
        return NoteList(
            play_notes=self.play_notes + other.play_notes,
            draw_notes=self.draw_notes + other.draw_notes,
            bars=self.bars + other.bars
        )

    def __iadd__(self, other: 'NoteList') -> 'NoteList':
        self.play_notes += other.play_notes
        self.draw_notes += other.draw_notes
        self.bars += other.bars
        return self

@dataclass
class CourseData:
    """A collection of course metadata
    level: number of stars
    balloon: list of balloon counts
    scoreinit: Unused
    scorediff: Unused
    is_branching: whether the course has branches
    """
    level: int = 0
    balloon: list[int] = field(default_factory=lambda: [])
    scoreinit: list[int] = field(default_factory=lambda: [])
    scorediff: int = 0
    is_branching: bool = False

@dataclass
class TJAMetadata:
    """Metadata for a TJA file
    title: dictionary for song titles, accessed by language code
    subtitle: dictionary for song subtitles, accessed by language code
    genre: genre of the song
    wave: path to the song's audio file
    demostart: start time of the preview
    offset: offset of the song's audio file
    bpm: beats per minute of the song
    bgmovie: path to the song's background movie file
    movieoffset: offset of the song's background movie file
    scene_preset: background for the song
    course_data: dictionary of course metadata, accessed by diff number
    """
    title: dict[str, str] = field(default_factory= lambda: {'en': ''})
    subtitle: dict[str, str] = field(default_factory= lambda: {'en': ''})
    genre: str = ''
    wave: Path = Path()
    demostart: float = 0.0
    offset: float = 0.0
    bpm: float = 120.0
    bgmovie: Path = Path()
    movieoffset: float = 0.0
    scene_preset: str = ''
    course_data: dict[int, CourseData] = field(default_factory=dict)

@dataclass
class TJAEXData:
    """Extra data for TJA files
    new_audio: Contains the word "-New Audio-" in any song title
    old_audio: Contains the word "-Old Audio-" in any song title
    limited_time: Contains the word "限定" in any song title or subtitle
    new: If the TJA file has been created or modified in the last week"""
    new_audio: bool = False
    old_audio: bool = False
    limited_time: bool = False
    new: bool = False


def calculate_base_score(notes: NoteList) -> int:
    """Calculate the base score for a song based on the number of notes, balloons, and drumrolls.

    Args:
        notes (NoteList): The list of notes in the song.

    Returns:
        int: The base score for the song.
    """
    total_notes = 0
    balloon_count = 0
    drumroll_msec = 0
    for i in range(len(notes.play_notes)):
        note = notes.play_notes[i]
        if i < len(notes.play_notes)-1:
            next_note = notes.play_notes[i+1]
        else:
            next_note = notes.play_notes[len(notes.play_notes)-1]
        if isinstance(note, Drumroll):
            drumroll_msec += (next_note.hit_ms - note.hit_ms)
        elif isinstance(note, Balloon):
            balloon_count += min(100, note.count)
        elif note.type == 8:
            continue
        else:
            total_notes += 1
    if total_notes == 0:
        return 1000000
    return math.ceil((1000000 - (balloon_count * 100) - (16.920079999994086 * drumroll_msec / 1000 * 100)) / total_notes / 10) * 10

def test_encodings(file_path):
    """Test the encoding of a file by trying different encodings.

    Args:
        file_path (Path): The path to the file to test.

    Returns:
        str: The encoding that successfully decoded the file.
    """
    encodings = ['utf-8-sig', 'shift-jis', 'utf-8']
    final_encoding = None

    for encoding in encodings:
        try:
            _ = file_path.read_text(encoding=encoding).splitlines()
            final_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    return final_encoding

logger = logging.getLogger(__name__)

class TJAParser:
    """Parse a TJA file and extract metadata and data.

    Args:
        path (Path): The path to the TJA file.
        start_delay (int): The delay in milliseconds before the first note.
        distance (int): The distance between notes.

    Attributes:
        metadata (TJAMetadata): The metadata extracted from the TJA file.
        ex_data (TJAEXData): The extended data extracted from the TJA file.
        data (list): The data extracted from the TJA file.
    """
    DIFFS = {0: "easy", 1: "normal", 2: "hard", 3: "oni", 4: "edit", 5: "tower", 6: "dan"}
    def __init__(self, path: Path, start_delay: int = 0, distance: int = 866):
        """
        Initialize a TJA object.

        Args:
            path (Path): The path to the TJA file.
            start_delay (int): The delay in milliseconds before the first note.
            distance (int): The distance between notes.
        """
        self.file_path: Path = path

        encoding = test_encodings(self.file_path)
        lines = self.file_path.read_text(encoding=encoding).splitlines()
        self.data = [cleaned for line in lines
                     if (cleaned := strip_comments(line).strip())]

        self.metadata = TJAMetadata()
        self.ex_data = TJAEXData()
        logger.debug(f"Parsing TJA file: {self.file_path}")
        self.get_metadata()

        self.distance = distance
        self.current_ms: float = start_delay

    def get_metadata(self):
        """
        Extract metadata from the TJA file.
        """
        current_diff = None  # Track which difficulty we're currently processing

        for item in self.data:
            if item.startswith('#BRANCH') and current_diff is not None:
                self.metadata.course_data[current_diff].is_branching = True
            elif item.startswith("#") or item[0].isdigit():
                continue
            elif item.startswith('SUBTITLE'):
                region_code = 'en'
                if item[len('SUBTITLE')] != ':':
                    region_code = (item[len('SUBTITLE'):len('SUBTITLE')+2]).lower()
                self.metadata.subtitle[region_code] = ''.join(item.split(':')[1:]).replace('--', '')
                if 'ja' in self.metadata.subtitle and '限定' in self.metadata.subtitle['ja']:
                    self.ex_data.limited_time = True
            elif item.startswith('TITLE'):
                region_code = 'en'
                if item[len('TITLE')] != ':':
                    region_code = (item[len('TITLE'):len('TITLE')+2]).lower()
                self.metadata.title[region_code] = ''.join(item.split(':')[1:])
            elif item.startswith('BPM'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid BPM value: {data} in TJA file {self.file_path}")
                    self.metadata.bpm = 0.0
                else:
                    self.metadata.bpm = float(data)
            elif item.startswith('WAVE'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid WAVE value: {data} in TJA file {self.file_path}")
                    self.metadata.wave = Path()
                else:
                    self.metadata.wave = self.file_path.parent / data.strip()
            elif item.startswith('OFFSET'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid OFFSET value: {data} in TJA file {self.file_path}")
                    self.metadata.offset = 0.0
                else:
                    self.metadata.offset = float(data)
            elif item.startswith('DEMOSTART'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid DEMOSTART value: {data} in TJA file {self.file_path}")
                    self.metadata.demostart = 0.0
                else:
                    self.metadata.demostart = float(data)
            elif item.startswith('BGMOVIE'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid BGMOVIE value: {data} in TJA file {self.file_path}")
                    self.metadata.bgmovie = Path()
                else:
                    self.metadata.bgmovie = self.file_path.parent / data.strip()
            elif item.startswith('MOVIEOFFSET'):
                data = item.split(':')[1]
                if not data:
                    logger.warning(f"Invalid MOVIEOFFSET value: {data} in TJA file {self.file_path}")
                    self.metadata.movieoffset = 0.0
                else:
                    self.metadata.movieoffset = float(data)
            elif item.startswith('SCENEPRESET'):
                self.metadata.scene_preset = item.split(':')[1]
            elif item.startswith('COURSE'):
                course = str(item.split(':')[1]).lower().strip()

                if course == '6' or course == 'dan':
                    current_diff = 6
                elif course == '5' or course == 'tower':
                    current_diff = 5
                elif course == '4' or course == 'edit' or course == 'ura':
                    current_diff = 4
                elif course == '3' or course == 'oni':
                    current_diff = 3
                elif course == '2' or course == 'hard':
                    current_diff = 2
                elif course == '1' or course == 'normal':
                    current_diff = 1
                elif course == '0' or course == 'easy':
                    current_diff = 0
                else:
                    logger.error(f"Course level empty in {self.file_path}")
                if current_diff is not None:
                    self.metadata.course_data[current_diff] = CourseData()
            elif current_diff is not None:
                if item.startswith('LEVEL'):
                    data = item.split(':')[1]
                    if not data:
                        self.metadata.course_data[current_diff].level = 0
                        logger.warning(f"Invalid LEVEL value: {data} in TJA file {self.file_path}")
                    else:
                        self.metadata.course_data[current_diff].level = int(float(data))
                elif item.startswith('BALLOONNOR'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        logger.debug(f"Invalid BALLOONNOR value: {balloon_data} in TJA file {self.file_path}")
                        continue
                    self.metadata.course_data[current_diff].balloon.extend([int(x) for x in balloon_data.split(',') if x != ''])
                elif item.startswith('BALLOONEXP'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        logger.debug(f"Invalid BALLOONEXP value: {balloon_data} in TJA file {self.file_path}")
                        continue
                    self.metadata.course_data[current_diff].balloon.extend([int(x) for x in balloon_data.split(',') if x != ''])
                elif item.startswith('BALLOONMAS'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        logger.debug(f"Invalid BALLOONMAS value: {balloon_data} in TJA file {self.file_path}")
                        continue
                    self.metadata.course_data[current_diff].balloon = [int(x) for x in balloon_data.split(',') if x != '']
                elif item.startswith('BALLOON'):
                    if item.find(':') == -1:
                        self.metadata.course_data[current_diff].balloon = []
                        continue
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        continue
                    self.metadata.course_data[current_diff].balloon = [int(x) for x in balloon_data.split(',') if x != '']
                elif item.startswith('SCOREINIT'):
                    score_init = item.split(':')[1]
                    if score_init == '':
                        continue
                    try:
                        self.metadata.course_data[current_diff].scoreinit = [int(x) for x in score_init.split(',') if x != '']
                    except Exception as e:
                        logger.error(f"Failed to parse SCOREINIT: {e} in TJA file {self.file_path}")
                        self.metadata.course_data[current_diff].scoreinit = [0, 0]
                elif item.startswith('SCOREDIFF'):
                    score_diff = item.split(':')[1]
                    if score_diff == '':
                        continue
                    self.metadata.course_data[current_diff].scorediff = int(float(score_diff))
        for region_code in self.metadata.title:
            if '-New Audio-' in self.metadata.title[region_code] or '-新曲-' in self.metadata.title[region_code]:
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-New Audio-', '')
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-新曲-', '')
                self.ex_data.new_audio = True
            elif '-Old Audio-' in self.metadata.title[region_code] or '-旧曲-' in self.metadata.title[region_code]:
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-Old Audio-', '')
                self.metadata.title[region_code] = self.metadata.title[region_code].replace('-旧曲-', '')
                self.ex_data.old_audio = True
            elif '限定' in self.metadata.title[region_code]:
                self.ex_data.limited_time = True

    def data_to_notes(self, diff) -> list[list[str]]:
        """
        Convert the data to notes.

        Args:
            diff (int): The difficulty level.

        Returns:
            list[list[str]]: The notes.
        """
        diff_name = self.DIFFS.get(diff, "").lower()

        # Use enumerate for single iteration
        note_start = note_end = -1
        target_found = False

        # Find the section boundaries
        for i, line in enumerate(self.data):
            if line.startswith("COURSE:"):
                course_value = line[7:].strip().lower()
                target_found = (course_value.isdigit() and int(course_value) == diff) or course_value == diff_name
            elif target_found:
                if note_start == -1 and line in ("#START", "#START P1"):
                    note_start = i + 1
                elif line == "#END" and note_start != -1:
                    note_end = i
                    break

        if note_start == -1 or note_end == -1:
            return []

        # Process the section with minimal string operations
        notes = []
        bar = []
        section_data = self.data[note_start:note_end]

        for line in section_data:
            if line.startswith("#"):
                bar.append(line)
            elif line == ',':
                if not bar or all(item.startswith('#') for item in bar):
                    bar.append('')
                notes.append(bar)
                bar = []
            else:
                if line.endswith(','):
                    bar.append(line[:-1])
                    notes.append(bar)
                    bar = []
                else:
                    bar.append(line)

        if bar:  # Add remaining items
            notes.append(bar)

        return notes

    def get_moji(self, play_note_list: list[Note], ms_per_measure: float) -> None:
        """
        Assign 口唱歌 (note phoneticization) to notes.
        Args:
            play_note_list (list[Note]): The list of notes to process.
            ms_per_measure (float): The duration of a measure in milliseconds.
        Returns:
            None
        """
        se_notes = {
            1: 0,
            2: 3,
            3: 5,
            4: 6,
            5: 7,
            6: 8,
            7: 9,
            8: 10,
            9: 11
        }
        if len(play_note_list) <= 1:
            return
        current_note = play_note_list[-1]
        if current_note.type == 1:
            current_note.moji = 0
        elif current_note.type == 2:
            current_note.moji = 3
        else:
            current_note.moji = se_notes[current_note.type]
        prev_note = play_note_list[-2]
        if prev_note.type == 1:
            timing_threshold = ms_per_measure / 8 - 1
            if current_note.hit_ms - prev_note.hit_ms <= timing_threshold:
                prev_note.moji = 1
            else:
                prev_note.moji = 0
        elif prev_note.type == 2:
            timing_threshold = ms_per_measure / 8 - 1
            if current_note.hit_ms - prev_note.hit_ms <= timing_threshold:
                prev_note.moji = 4
            else:
                prev_note.moji = 3
        else:
            prev_note.moji = se_notes[prev_note.type]
        if len(play_note_list) > 3:
            notes_minus_4 = play_note_list[-4]
            notes_minus_3 = play_note_list[-3]
            notes_minus_2 = play_note_list[-2]
            consecutive_ones = (
                notes_minus_4.type == 1 and
                notes_minus_3.type == 1 and
                notes_minus_2.type == 1
            )
            if consecutive_ones:
                rapid_timing = (
                    notes_minus_3.hit_ms - notes_minus_4.hit_ms < (ms_per_measure / 8) and
                    notes_minus_2.hit_ms - notes_minus_3.hit_ms < (ms_per_measure / 8)
                )
                if rapid_timing:
                    if len(play_note_list) > 5:
                        spacing_before = play_note_list[-4].hit_ms - play_note_list[-5].hit_ms >= (ms_per_measure / 8)
                        spacing_after = play_note_list[-1].hit_ms - play_note_list[-2].hit_ms >= (ms_per_measure / 8)
                        if spacing_before and spacing_after:
                            play_note_list[-3].moji = 2
                    else:
                        play_note_list[-3].moji = 2

    def notes_to_position(self, diff: int):
        """Parse a TJA's notes into a NoteList."""
        master_notes = NoteList()
        branch_m: list[NoteList] = []
        branch_e: list[NoteList] = []
        branch_n: list[NoteList] = []
        notes = self.data_to_notes(diff)
        balloon = self.metadata.course_data[diff].balloon.copy()
        count = 0
        index = 0
        time_signature = 4/4
        bpm = self.metadata.bpm
        x_scroll_modifier = 1
        y_scroll_modifier = 0
        barline_display = True
        gogo_time = False
        curr_note_list = master_notes.play_notes
        curr_draw_list = master_notes.draw_notes
        curr_bar_list = master_notes.bars
        start_branch_ms = 0
        start_branch_bpm = bpm
        start_branch_time_sig = time_signature
        start_branch_x_scroll = x_scroll_modifier
        start_branch_y_scroll = y_scroll_modifier
        start_branch_barline = barline_display
        start_branch_gogo = gogo_time
        branch_balloon_count = 0
        is_branching = False
        prev_note = None
        for bar in notes:
            #Length of the bar is determined by number of notes excluding commands
            bar_length = sum(len(part) for part in bar if '#' not in part)
            barline_added = False
            for part in bar:
                if part.startswith('#BRANCHSTART'):
                    start_branch_ms = self.current_ms
                    start_branch_bpm = bpm
                    start_branch_time_sig = time_signature
                    start_branch_x_scroll = x_scroll_modifier
                    start_branch_y_scroll = y_scroll_modifier
                    start_branch_barline = barline_display
                    start_branch_gogo = gogo_time
                    branch_balloon_count = count
                    branch_params = part[13:]

                    if branch_params[0] == 'r':
                        # Helper function to find and set drumroll branch params
                        def set_drumroll_branch_params(note_list, bar_list):
                            for i in range(len(note_list)-1, -1, -1):
                                if 5 <= note_list[i].type <= 7 or note_list[i].type == 9:
                                    drumroll_ms = note_list[i].hit_ms
                                    for bar_idx in range(len(bar_list)-1, -1, -1):
                                        if bar_list[bar_idx].hit_ms <= drumroll_ms:
                                            bar_list[bar_idx].branch_params = branch_params
                                            return True
                                    break
                            return False

                        # Always try to set in master notes
                        set_drumroll_branch_params(master_notes.play_notes, master_notes.bars)

                        # If we have existing branches, also apply to them
                        if branch_m and len(branch_m) > 0:
                            set_drumroll_branch_params(branch_m[-1].play_notes, branch_m[-1].bars)
                        if branch_e and len(branch_e) > 0:
                            set_drumroll_branch_params(branch_e[-1].play_notes, branch_e[-1].bars)
                        if branch_n and len(branch_n) > 0:
                            set_drumroll_branch_params(branch_n[-1].play_notes, branch_n[-1].bars)
                    else:
                        if len(curr_bar_list) > 1:
                            curr_bar_list[-2].branch_params = branch_params
                        elif len(curr_bar_list) > 0:
                            curr_bar_list[-1].branch_params = branch_params

                        if branch_m and len(branch_m[-1].bars) > 1:
                            branch_m[-1].bars[-2].branch_params = branch_params
                        elif branch_m and len(branch_m[-1].bars) > 0:
                            branch_m[-1].bars[-1].branch_params = branch_params
                        if branch_e and len(branch_e[-1].bars) > 1:
                            branch_e[-1].bars[-2].branch_params = branch_params
                        elif branch_e and len(branch_e[-1].bars) > 0:
                            branch_e[-1].bars[-1].branch_params = branch_params
                        if branch_n and len(branch_n[-1].bars) > 1:
                            branch_n[-1].bars[-2].branch_params = branch_params
                        elif branch_n and len(branch_n[-1].bars) > 0:
                            branch_n[-1].bars[-1].branch_params = branch_params
                        if branch_m and len(branch_m[-1].bars) > 0:
                            branch_m[-1].bars[-1].branch_params = branch_params
                    continue
                elif part.startswith('#BRANCHEND'):
                    curr_note_list = master_notes.play_notes
                    curr_draw_list = master_notes.draw_notes
                    curr_bar_list = master_notes.bars
                    continue
                if part == '#M':
                    branch_m.append(NoteList())
                    curr_note_list = branch_m[-1].play_notes
                    curr_draw_list = branch_m[-1].draw_notes
                    curr_bar_list = branch_m[-1].bars
                    self.current_ms = start_branch_ms
                    bpm = start_branch_bpm
                    time_signature = start_branch_time_sig
                    x_scroll_modifier = start_branch_x_scroll
                    y_scroll_modifier = start_branch_y_scroll
                    barline_display = start_branch_barline
                    gogo_time = start_branch_gogo
                    count = branch_balloon_count
                    is_branching = True
                    continue
                elif part == '#E':
                    branch_e.append(NoteList())
                    curr_note_list = branch_e[-1].play_notes
                    curr_draw_list = branch_e[-1].draw_notes
                    curr_bar_list = branch_e[-1].bars
                    self.current_ms = start_branch_ms
                    bpm = start_branch_bpm
                    time_signature = start_branch_time_sig
                    x_scroll_modifier = start_branch_x_scroll
                    y_scroll_modifier = start_branch_y_scroll
                    barline_display = start_branch_barline
                    gogo_time = start_branch_gogo
                    count = branch_balloon_count
                    is_branching = True
                    continue
                elif part == '#N':
                    branch_n.append(NoteList())
                    curr_note_list = branch_n[-1].play_notes
                    curr_draw_list = branch_n[-1].draw_notes
                    curr_bar_list = branch_n[-1].bars
                    self.current_ms = start_branch_ms
                    bpm = start_branch_bpm
                    time_signature = start_branch_time_sig
                    x_scroll_modifier = start_branch_x_scroll
                    y_scroll_modifier = start_branch_y_scroll
                    barline_display = start_branch_barline
                    gogo_time = start_branch_gogo
                    count = branch_balloon_count
                    is_branching = True
                    continue
                if '#LYRIC' in part:
                    continue
                if '#JPOSSCROLL' in part:
                    continue
                elif '#NMSCROLL' in part:
                    continue
                elif '#MEASURE' in part:
                    divisor = part.find('/')
                    time_signature = float(part[9:divisor]) / float(part[divisor+1:])
                    continue
                elif '#SCROLL' in part:
                    scroll_value = part[7:]
                    if 'i' in scroll_value:
                        normalized = scroll_value.replace('.i', 'j').replace('i', 'j')
                        c = complex(normalized)
                        x_scroll_modifier = c.real
                        y_scroll_modifier = c.imag
                    else:
                        x_scroll_modifier = float(scroll_value)
                        y_scroll_modifier = 0.0
                    continue
                elif '#BPMCHANGE' in part:
                    bpm = float(part[11:])
                    continue
                elif '#BARLINEOFF' in part:
                    barline_display = False
                    continue
                elif '#BARLINEON' in part:
                    barline_display = True
                    continue
                elif '#GOGOSTART' in part:
                    gogo_time = True
                    continue
                elif '#GOGOEND' in part:
                    gogo_time = False
                    continue
                #Unrecognized commands will be skipped for now
                elif len(part) > 0 and not part[0].isdigit():
                    continue

                ms_per_measure = get_ms_per_measure(bpm, time_signature)

                #Create note object
                bar_line = Note()

                #Determines how quickly the notes need to move across the screen to reach the judgment circle in time
                bar_line.pixels_per_frame_x = get_pixels_per_frame(bpm * time_signature * x_scroll_modifier, time_signature*4, self.distance)
                bar_line.pixels_per_frame_y = get_pixels_per_frame(bpm * time_signature * y_scroll_modifier, time_signature*4, self.distance)
                pixels_per_ms = get_pixels_per_ms(bar_line.pixels_per_frame_x)

                bar_line.hit_ms = self.current_ms
                if pixels_per_ms == 0:
                    bar_line.load_ms = bar_line.hit_ms
                else:
                    bar_line.load_ms = bar_line.hit_ms - (self.distance / pixels_per_ms)
                bar_line.type = 0
                bar_line.display = barline_display
                bar_line.gogo_time = gogo_time
                bar_line.bpm = bpm
                if barline_added:
                    bar_line.display = False

                if is_branching:
                    bar_line.is_branch_start = True
                    is_branching = False

                bisect.insort(curr_bar_list, bar_line, key=lambda x: x.load_ms)
                barline_added = True

                #Empty bar is still a bar, otherwise start increment
                if len(part) == 0:
                    self.current_ms += ms_per_measure
                    increment = 0
                else:
                    increment = ms_per_measure / bar_length

                for item in part:
                    if item == '.':
                        continue
                    if item == '0' or (not item.isdigit()):
                        self.current_ms += increment
                        continue
                    if item == '9' and curr_note_list and curr_note_list[-1].type == 9:
                        self.current_ms += increment
                        continue
                    note = Note()
                    note.hit_ms = self.current_ms
                    note.display = True
                    note.pixels_per_frame_x = bar_line.pixels_per_frame_x
                    note.pixels_per_frame_y = bar_line.pixels_per_frame_y
                    pixels_per_ms = get_pixels_per_ms(note.pixels_per_frame_x)
                    note.load_ms = (note.hit_ms if pixels_per_ms == 0
                                    else note.hit_ms - (self.distance / pixels_per_ms))
                    note.type = int(item)
                    note.index = index
                    note.bpm = bpm
                    note.gogo_time = gogo_time
                    note.moji = -1
                    if item in {'5', '6'}:
                        note = Drumroll(note)
                        note.color = 255
                    elif item in {'7', '9'}:
                        count += 1
                        if balloon is None:
                            raise Exception("Balloon note found, but no count was specified")
                        if item == '9':
                            note = Balloon(note, is_kusudama=True)
                        else:
                            note = Balloon(note)
                        note.count = 1 if not balloon else balloon.pop(0)
                    elif item == '8':
                        if prev_note is None:
                            raise ValueError("No previous note found")
                        new_pixels_per_ms = prev_note.pixels_per_frame_x / (1000 / 60)
                        if new_pixels_per_ms == 0:
                            note.load_ms = note.hit_ms
                        else:
                            note.load_ms = note.hit_ms - (self.distance / new_pixels_per_ms)
                        note.pixels_per_frame_x = prev_note.pixels_per_frame_x
                    self.current_ms += increment
                    curr_note_list.append(note)
                    bisect.insort(curr_draw_list, note, key=lambda x: x.load_ms)
                    self.get_moji(curr_note_list, ms_per_measure)
                    index += 1
                    prev_note = note
        # Sorting by load_ms is necessary for drawing, as some notes appear on the
        # screen slower regardless of when they reach the judge circle
        # Bars can be sorted like this because they don't need hit detection
        return master_notes, branch_m, branch_e, branch_n

    def hash_note_data(self, notes: NoteList):
        """Hashes the note data for the given NoteList."""
        n = hashlib.sha256()
        list1 = notes.play_notes
        list2 = notes.bars
        merged: list[Note | Drumroll | Balloon] = []
        i = 0
        j = 0
        while i < len(list1) and j < len(list2):
            if list1[i] <= list2[j]:
                merged.append(list1[i])
                i += 1
            else:
                merged.append(list2[j])
                j += 1
        merged.extend(list1[i:])
        merged.extend(list2[j:])
        for item in merged:
            n.update(item.get_hash().encode('utf-8'))

        return n.hexdigest()

def modifier_speed(notes: NoteList, value: float):
    """Modifies the speed of the notes in the given NoteList."""
    modded_notes = notes.draw_notes.copy()
    modded_bars = notes.bars.copy()
    for note in modded_notes:
        note.pixels_per_frame_x *= value
        note.load_ms = note.hit_ms - (866 / get_pixels_per_ms(note.pixels_per_frame_x))
    for bar in modded_bars:
        bar.pixels_per_frame_x *= value
        bar.load_ms = bar.hit_ms - (866 / get_pixels_per_ms(bar.pixels_per_frame_x))
    return modded_notes, modded_bars

def modifier_display(notes: NoteList):
    """Modifies the display of the notes in the given NoteList."""
    modded_notes = notes.draw_notes.copy()
    for note in modded_notes:
        note.display = False
    return modded_notes

def modifier_inverse(notes: NoteList):
    """Inverts the type of the notes in the given NoteList."""
    modded_notes = notes.play_notes.copy()
    type_mapping = {1: 2, 2: 1, 3: 4, 4: 3}
    for note in modded_notes:
        if note.type in type_mapping:
            note.type = type_mapping[note.type]
    return modded_notes

def modifier_random(notes: NoteList, value: int):
    """Randomly modifies the type of the notes in the given NoteList.
    value: 1 == kimagure, 2 == detarame"""
    #value: 1 == kimagure, 2 == detarame
    modded_notes = notes.play_notes.copy()
    percentage = int(len(modded_notes) / 5) * value
    selected_notes = random.sample(range(len(modded_notes)), percentage)
    type_mapping = {1: 2, 2: 1, 3: 4, 4: 3}
    for i in selected_notes:
        if modded_notes[i].type in type_mapping:
            modded_notes[i].type = type_mapping[modded_notes[i].type]
    return modded_notes

def apply_modifiers(notes: NoteList, modifiers: Modifiers):
    """Applies all selected modifiers from global_data to the given NoteList."""
    if modifiers.display:
        draw_notes = modifier_display(notes)
    if modifiers.inverse:
        play_notes = modifier_inverse(notes)
    play_notes = modifier_random(notes, modifiers.random)
    draw_notes, bars = modifier_speed(notes, modifiers.speed)
    return deque(play_notes), deque(draw_notes), deque(bars)
