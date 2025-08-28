import bisect
import hashlib
import math
import random
from collections import deque
from dataclasses import dataclass, field, fields
from functools import lru_cache
from pathlib import Path

from libs.utils import get_pixels_per_frame, global_data, strip_comments


@lru_cache(maxsize=64)
def get_ms_per_measure(bpm_val, time_sig):
    #https://gist.github.com/KatieFrogs/e000f406bbc70a12f3c34a07303eec8b#measure
    if bpm_val == 0:
        return 0
    return 60000 * (time_sig * 4) / bpm_val

@lru_cache(maxsize=64)
def get_pixels_per_ms(pixels_per_frame):
    return pixels_per_frame / (1000 / 60)

@dataclass()
class Note:
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

    def __le__(self, other):
        return self.hit_ms <= other.hit_ms

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
class CourseData:
    level: int = 0
    balloon: list[int] = field(default_factory=lambda: [])
    scoreinit: list[int] = field(default_factory=lambda: [])
    scorediff: int = 0

@dataclass
class TJAMetadata:
    title: dict[str, str] = field(default_factory= lambda: {'en': ''})
    subtitle: dict[str, str] = field(default_factory= lambda: {'en': ''})
    genre: str = ''
    wave: Path = Path()
    demostart: float = 0.0
    offset: float = 0.0
    bpm: float = 120.0
    bgmovie: Path = Path()
    movieoffset: float = 0.0
    course_data: dict[int, CourseData] = field(default_factory=dict)

@dataclass
class TJAEXData:
    new_audio: bool = False
    old_audio: bool = False
    limited_time: bool = False
    new: bool = False


def calculate_base_score(play_note_list: deque[Note | Drumroll | Balloon]) -> int:
    total_notes = 0
    balloon_num = 0
    balloon_count = 0
    drumroll_sec = 0
    for i in range(len(play_note_list)):
        note = play_note_list[i]
        if i < len(play_note_list)-1:
            next_note = play_note_list[i+1]
        else:
            next_note = play_note_list[len(play_note_list)-1]
        if isinstance(note, Drumroll):
            drumroll_sec += (next_note.hit_ms - note.hit_ms) / 1000
        elif isinstance(note, Balloon):
            balloon_num += 1
            balloon_count += note.count
        else:
            total_notes += 1
    if total_notes == 0:
        return 0
    total_score = (1000000 - (balloon_count * 100) - (drumroll_sec * 1692.0079999994086)) / total_notes
    return math.ceil(total_score / 10) * 10

def test_encodings(file_path):
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


class TJAParser:
    DIFFS = {0: "easy", 1: "normal", 2: "hard", 3: "oni", 4: "edit", 5: "tower", 6: "dan"}
    def __init__(self, path: Path, start_delay: int = 0, distance: int = 866):
        self.file_path: Path = path

        encoding = test_encodings(self.file_path)
        lines = self.file_path.read_text(encoding=encoding).splitlines()
        self.data = [cleaned for line in lines
                     if (cleaned := strip_comments(line).strip())]

        self.metadata = TJAMetadata()
        self.ex_data = TJAEXData()
        self.get_metadata()

        self.distance = distance
        self.current_ms: float = start_delay

    def get_metadata(self):
        current_diff = None  # Track which difficulty we're currently processing

        for item in self.data:
            if item.startswith("#") or item[0].isdigit():
                continue
            elif item.startswith('SUBTITLE'):
                region_code = 'en'
                if item[len('SUBTITLE')] != ':':
                    region_code = (item[len('SUBTITLE'):len('SUBTITLE')+2]).lower()
                self.metadata.subtitle[region_code] = ''.join(item.split(':')[1:])
                if 'ja' in self.metadata.subtitle and '限定' in self.metadata.subtitle['ja']:
                    self.ex_data.limited_time = True
            elif item.startswith('TITLE'):
                region_code = 'en'
                if item[len('TITLE')] != ':':
                    region_code = (item[len('TITLE'):len('TITLE')+2]).lower()
                self.metadata.title[region_code] = ''.join(item.split(':')[1:])
            elif item.startswith('BPM'):
                self.metadata.bpm = float(item.split(':')[1])
            elif item.startswith('WAVE'):
                self.metadata.wave = self.file_path.parent / item.split(':')[1].strip()
            elif item.startswith('OFFSET'):
                self.metadata.offset = float(item.split(':')[1])
            elif item.startswith('DEMOSTART'):
                self.metadata.demostart = float(item.split(':')[1]) if item.split(':')[1] != '' else 0
            elif item.startswith('BGMOVIE'):
                self.metadata.bgmovie = self.file_path.parent / item.split(':')[1].strip()
            elif item.startswith('MOVIEOFFSET'):
                self.metadata.movieoffset = float(item.split(':')[1])
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
                    raise Exception("course level empty")
                self.metadata.course_data[current_diff] = CourseData()
            elif current_diff is not None:
                if item.startswith('LEVEL'):
                    self.metadata.course_data[current_diff].level = int(float(item.split(':')[1]))
                elif item.startswith('BALLOONNOR'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        continue
                    self.metadata.course_data[current_diff].balloon.extend([int(x) for x in balloon_data.split(',') if x != ''])
                elif item.startswith('BALLOONEXP'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
                        continue
                    self.metadata.course_data[current_diff].balloon.extend([int(x) for x in balloon_data.split(',') if x != ''])
                elif item.startswith('BALLOONMAS'):
                    balloon_data = item.split(':')[1]
                    if balloon_data == '':
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
                        print("Failed to parse SCOREINIT: ", e)
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
        se_notes = {
            1: [0, 1, 2],  # Note '1' has three possible sound effects
            2: [3, 4],     # Note '2' has two possible sound effects
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
        if current_note.type in {1, 2}:
            current_note.moji = se_notes[current_note.type][0]
        else:
            current_note.moji = se_notes[current_note.type]

        prev_note = play_note_list[-2]

        if prev_note.type in {1, 2}:
            timing_threshold = ms_per_measure / 8 - 1
            if current_note.hit_ms - prev_note.hit_ms <= timing_threshold:
                prev_note.moji = se_notes[prev_note.type][1]
            else:
                prev_note.moji = se_notes[prev_note.type][0]
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
                            play_note_list[-3].moji = se_notes[1][2]
                    else:
                        play_note_list[-3].moji = se_notes[1][2]

    def notes_to_position(self, diff: int):
        play_note_list: list[Note | Drumroll | Balloon] = []
        draw_note_list: list[Note | Drumroll | Balloon] = []
        bar_list: list[Note] = []
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
        skip_branch = False
        for bar in notes:
            #Length of the bar is determined by number of notes excluding commands
            bar_length = sum(len(part) for part in bar if '#' not in part)
            barline_added = False
            for part in bar:
                if '#LYRIC' in part:
                    continue
                if part.startswith('#BRANCHSTART'):
                    skip_branch = True
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
                    # Extract the value after '#SCROLL '
                    scroll_value = part[7:].strip()  # Remove '#SCROLL' and whitespace

                    # Initialize default values
                    x_scroll_modifier = 0
                    y_scroll_modifier = 0

                    # Handle empty value
                    if not scroll_value:
                        continue

                    # Check if it's a complex number (contains 'i')
                    if 'i' in scroll_value:
                        # Handle different imaginary number formats
                        if scroll_value == 'i':
                            x_scroll_modifier = 0
                            y_scroll_modifier = 1
                        elif scroll_value == '-i':
                            x_scroll_modifier = 0
                            y_scroll_modifier = -1
                        elif scroll_value.endswith('i') or scroll_value.endswith('.i'):
                            # Remove the 'i' or '.i' suffix
                            if scroll_value.endswith('.i'):
                                complex_part = scroll_value[:-2]
                            else:
                                complex_part = scroll_value[:-1]

                            # Look for + or - that separates real and imaginary parts
                            # Find the rightmost + or - (excluding position 0 for negative numbers)
                            plus_pos = complex_part.rfind('+')
                            minus_pos = complex_part.rfind('-')

                            separator_pos = -1
                            if plus_pos > 0:  # Ignore + at position 0
                                separator_pos = plus_pos
                            if minus_pos > 0 and minus_pos > separator_pos:  # Ignore - at position 0
                                separator_pos = minus_pos

                            if separator_pos > 0:
                                # Complex number like '1+i', '3+4i', '2-5i', '-1+2i', etc.
                                real_part = complex_part[:separator_pos]
                                imag_part = complex_part[separator_pos:]

                                x_scroll_modifier = float(real_part) if real_part else 0

                                # Handle imaginary part
                                if imag_part == '+' or imag_part == '':
                                    y_scroll_modifier = 1
                                elif imag_part == '-':
                                    y_scroll_modifier = -1
                                else:
                                    y_scroll_modifier = float(imag_part)
                            else:
                                # Pure imaginary like '5i', '-3i', '2.5i'
                                if complex_part == '' or complex_part == '+':
                                    y_scroll_modifier = 1
                                elif complex_part == '-':
                                    y_scroll_modifier = -1
                                else:
                                    y_scroll_modifier = float(complex_part)
                                x_scroll_modifier = 0
                        else:
                            # 'i' is somewhere in the middle - invalid format
                            continue
                    else:
                        # Pure real number
                        x_scroll_modifier = float(scroll_value)
                        y_scroll_modifier = 0
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
                elif part.startswith('#M'):
                    skip_branch = False
                    continue
                #Unrecognized commands will be skipped for now
                elif len(part) > 0 and not part[0].isdigit():
                    continue
                if skip_branch:
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
                bar_line.bpm = bpm
                if barline_added:
                    bar_line.display = False

                bisect.insort(bar_list, bar_line, key=lambda x: x.load_ms)
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
                        new_pixels_per_ms = play_note_list[-1].pixels_per_frame_x / (1000 / 60)
                        if new_pixels_per_ms == 0:
                            note.load_ms = note.hit_ms
                        else:
                            note.load_ms = note.hit_ms - (self.distance / new_pixels_per_ms)
                        note.pixels_per_frame_x = play_note_list[-1].pixels_per_frame_x
                    self.current_ms += increment
                    play_note_list.append(note)
                    bisect.insort(draw_note_list, note, key=lambda x: x.load_ms)
                    self.get_moji(play_note_list, ms_per_measure)
                    index += 1
                    if len(play_note_list) > 3:
                        if isinstance(play_note_list[-2], Drumroll) and play_note_list[-1].type != 8:
                            print(self.file_path, diff)
                            print(bar)
                            continue
                            raise Exception(f"{play_note_list[-2]}")
        # https://stackoverflow.com/questions/72899/how-to-sort-a-list-of-dictionaries-by-a-value-of-the-dictionary-in-python
        # Sorting by load_ms is necessary for drawing, as some notes appear on the
        # screen slower regardless of when they reach the judge circle
        # Bars can be sorted like this because they don't need hit detection
        return deque(play_note_list), deque(draw_note_list), deque(bar_list)

    def hash_note_data(self, play_notes: deque[Note | Drumroll | Balloon], bars: deque[Note]):
        n = hashlib.sha256()
        list1 = list(play_notes)
        list2 = list(bars)
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

def modifier_speed(notes: deque[Note | Balloon | Drumroll], bars, value: float):
    notes = notes.copy()
    for note in notes:
        note.pixels_per_frame_x *= value
        note.load_ms = note.hit_ms - (866 / get_pixels_per_ms(note.pixels_per_frame_x))
    for bar in bars:
        bar.pixels_per_frame_x *= value
        bar.load_ms = bar.hit_ms - (866 / get_pixels_per_ms(bar.pixels_per_frame_x))
    return notes, bars

def modifier_display(notes: deque[Note | Balloon | Drumroll]):
    notes = notes.copy()
    for note in notes:
        note.display = False
    return notes

def modifier_inverse(notes: deque[Note | Balloon | Drumroll]):
    notes = notes.copy()
    type_mapping = {1: 2, 2: 1, 3: 4, 4: 3}
    for note in notes:
        if note.type in type_mapping:
            note.type = type_mapping[note.type]
    return notes

def modifier_random(notes: deque[Note | Balloon | Drumroll], value: int):
    #value: 1 == kimagure, 2 == detarame
    notes = notes.copy()
    percentage = int(len(notes) / 5) * value
    selected_notes = random.sample(range(len(notes)), percentage)
    type_mapping = {1: 2, 2: 1, 3: 4, 4: 3}
    for i in selected_notes:
        if notes[i].type in type_mapping:
            notes[i].type = type_mapping[notes[i].type]
    return notes

def apply_modifiers(notes: deque[Note | Balloon | Drumroll], draw_notes: deque[Note | Balloon | Drumroll], bars: deque[Note]):
    if global_data.modifiers.display:
        draw_notes = modifier_display(draw_notes)
    if global_data.modifiers.inverse:
        notes = modifier_inverse(notes)
    notes = modifier_random(notes, global_data.modifiers.random)
    draw_notes, bars = modifier_speed(draw_notes, bars, global_data.modifiers.speed)
    return notes, draw_notes, bars
