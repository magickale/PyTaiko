import math
from collections import deque

from libs.utils import get_pixels_per_frame, strip_comments


def calculate_base_score(play_note_list: deque[dict]) -> int:
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
        if note.get('note') in {'1','2','3','4'}:
            total_notes += 1
        elif note.get('note') in {'5', '6'}:
            drumroll_sec += (next_note['ms'] - note['ms']) / 1000
        elif note.get('note') in {'7', '9'}:
            balloon_num += 1
            balloon_count += next_note['balloon']
    total_score = (1000000 - (balloon_count * 100) - (drumroll_sec * 1692.0079999994086)) / total_notes
    return math.ceil(total_score / 10) * 10

class TJAParser:
    def __init__(self, path: str):
        #Defined on startup
        self.folder_path = path
        self.folder_name = self.folder_path.split('\\')[-1]
        self.file_path = f'{self.folder_path}\\{self.folder_name}.tja'

        #Defined on file_to_data()
        self.data = []

        #Defined on get_metadata()
        self.title = ''
        self.title_ja = ''
        self.subtitle = ''
        self.subtitle_ja = ''
        self.wave = f'{self.folder_path}\\'
        self.offset = 0
        self.demo_start = 0
        self.course_data = dict()

        #Defined in metadata but can change throughout the chart
        self.bpm = 120
        self.time_signature = 4/4

        self.distance = 0
        self.scroll_modifier = 1
        self.current_ms = 0
        self.barline_display = True
        self.gogo_time = False

    def _file_to_data(self):
        with open(self.file_path, 'rt', encoding='utf-8-sig') as tja_file:
            for line in tja_file:
                line = strip_comments(line).strip()
                if line != '':
                    self.data.append(str(line))
            return self.data

    def get_metadata(self):
        self._file_to_data()
        diff_index = 1
        highest_diff = -1
        for item in self.data:
            if item[0] == '#':
                continue
            elif 'SUBTITLEJA' in item:
                self.subtitle_ja = str(item.split('SUBTITLEJA:')[1])
            elif 'TITLEJA' in item:
                self.title_ja = str(item.split('TITLEJA:')[1])
            elif 'SUBTITLE' in item:
                self.subtitle = str(item.split('SUBTITLE:')[1][2:])
            elif 'TITLE' in item:
                self.title = str(item.split('TITLE:')[1])
            elif 'BPM' in item:
                self.bpm = float(item.split(':')[1])
            elif 'WAVE' in item:
                self.wave += str(item.split(':')[1])
            elif 'OFFSET' in item:
                self.offset = float(item.split(':')[1])
            elif 'DEMOSTART' in item:
                self.demo_start = float(item.split(':')[1])
            elif 'COURSE' in item:
                course = str(item.split(':')[1]).lower()
                if course == 'dan' or course == '6':
                    self.course_data[6] = []
                if course == 'tower' or course == '5':
                    self.course_data[5] = []
                elif course == 'edit' or course == '4':
                    self.course_data[4] = []
                elif course == 'oni' or course == '3':
                    self.course_data[3] = []
                elif course == 'hard' or course == '2':
                    self.course_data[2] = []
                elif course == 'normal' or course == '1':
                    self.course_data[1] = []
                elif course == 'easy' or course == '0':
                    self.course_data[0] = []
                highest_diff = max(self.course_data)
                diff_index -= 1
            elif 'LEVEL' in item:
                item = int(item.split(':')[1])
                self.course_data[diff_index+highest_diff].append(item)
            elif 'BALLOON' in item:
                item = item.split(':')[1]
                if item == '':
                    continue
                self.course_data[diff_index+highest_diff].append([int(x) for x in item.split(',')])
            elif 'SCOREINIT' in item:
                if item.split(':')[1] == '':
                    continue
                item = item.split(':')[1]
                self.course_data[diff_index+highest_diff].append([int(x) for x in item.split(',')])
            elif 'SCOREDIFF' in item:
                if item.split(':')[1] == '':
                    continue
                item = int(item.split(':')[1])
                self.course_data[diff_index+highest_diff].append(item)
        return [self.title, self.title_ja, self.subtitle, self.subtitle_ja,
            self.bpm, self.wave, self.offset, self.demo_start, self.course_data]

    def data_to_notes(self, diff):
        self._file_to_data()
        #Get notes start and end
        note_start = -1
        note_end = -1
        diff_count = 0
        for i in range(len(self.data)):
            if self.data[i] == '#START':
                note_start = i+1
            elif self.data[i] == '#END':
                note_end = i
                diff_count += 1
            if diff_count == len(self.course_data) - diff:
                break

        notes = []
        bar = []
        #Check for measures and separate when comma exists
        for i in range(note_start, note_end):
            line = self.data[i]
            if line.startswith("#"):
                bar.append(line)
            else:
                item = line.strip(',')
                if item == '':
                    if bar == []:
                        bar.append(item)
                    else:
                        notes.append(bar)
                        bar = []
                        continue
                else:
                    bar.append(item)
                    if item != line:
                        notes.append(bar)
                        bar = []
        if len(self.course_data[diff]) < 2:
            return notes, None
        return notes, self.course_data[diff][1]

    def get_se_note(self, play_note_list, ms_per_measure, note, note_ms):
        #Someone please refactor this
        se_notes = {'1': [0, 1, 2],
            '2': [3, 4],
            '3': 5,
            '4': 6,
            '5': 7,
            '6': 14,
            '7': 9,
            '8': 10,
            '9': 11}
        if len(play_note_list) > 1:
            prev_note = play_note_list[-2]
            if prev_note['note'] in {'1', '2'}:
                if note_ms - prev_note['ms'] <= (ms_per_measure/8) - 1:
                    prev_note['se_note'] = se_notes[prev_note['note']][1]
                else:
                    prev_note['se_note'] = se_notes[prev_note['note']][0]
            else:
                prev_note['se_note'] = se_notes[prev_note['note']]
            if len(play_note_list) > 3:
                if play_note_list[-4]['note'] == play_note_list[-3]['note'] == play_note_list[-2]['note'] == '1':
                    if (play_note_list[-3]['ms'] - play_note_list[-4]['ms'] < (ms_per_measure/8)) and (play_note_list[-2]['ms'] - play_note_list[-3]['ms'] < (ms_per_measure/8)):
                        if len(play_note_list) > 5:
                            if (play_note_list[-4]['ms'] - play_note_list[-5]['ms'] >= (ms_per_measure/8)) and (play_note_list[-1]['ms'] - play_note_list[-2]['ms'] >= (ms_per_measure/8)):
                                play_note_list[-3]['se_note'] = se_notes[play_note_list[-3]['note']][2]
                        else:
                            play_note_list[-3]['se_note'] = se_notes[play_note_list[-3]['note']][2]
        else:
            play_note_list[-1]['se_note'] = se_notes[note]
        if play_note_list[-1]['note'] in {'1', '2'}:
            play_note_list[-1]['se_note'] = se_notes[note][0]
        else:
            play_note_list[-1]['se_note'] = se_notes[note]

    def notes_to_position(self, diff):
        play_note_list = deque()
        bar_list = deque()
        draw_note_list = deque()
        notes, balloon = self.data_to_notes(diff)
        index = 0
        balloon_index = 0
        for bar in notes:
            #Length of the bar is determined by number of notes excluding commands
            bar_length = sum(len(part) for part in bar if '#' not in part)

            for part in bar:
                if '#JPOSSCROLL' in part:
                    continue
                elif '#NMSCROLL' in part:
                    continue
                elif '#MEASURE' in part:
                    divisor = part.find('/')
                    self.time_signature = float(part[9:divisor]) / float(part[divisor+1:])
                    continue
                elif '#SCROLL' in part:
                    self.scroll_modifier = float(part[7:])
                    continue
                elif '#BPMCHANGE' in part:
                    self.bpm = float(part[11:])
                    continue
                elif '#BARLINEOFF' in part:
                    self.barline_display = False
                    continue
                elif '#BARLINEON' in part:
                    self.barline_display = True
                    continue
                elif '#GOGOSTART' in part:
                    self.gogo_time = True
                    continue
                elif '#GOGOEND' in part:
                    self.gogo_time = False
                    continue
                elif '#LYRIC' in part:
                    continue
                #Unrecognized commands will be skipped for now
                elif '#' in part:
                    continue

                #https://gist.github.com/KatieFrogs/e000f406bbc70a12f3c34a07303eec8b#measure
                ms_per_measure = 60000 * (self.time_signature*4) / self.bpm

                #Determines how quickly the notes need to move across the screen to reach the judgment circle in time
                pixels_per_frame = get_pixels_per_frame(self.bpm * self.time_signature * self.scroll_modifier, self.time_signature*4, self.distance)
                pixels_per_ms = pixels_per_frame / (1000 / 60)

                bar_ms = self.current_ms
                load_ms = bar_ms - (self.distance / pixels_per_ms)

                if self.barline_display:
                    bar_list.append({'note': 'barline', 'ms': bar_ms, 'load_ms': load_ms, 'ppf': pixels_per_frame})

                #Empty bar is still a bar, otherwise start increment
                if len(part) == 0:
                    self.current_ms += ms_per_measure
                    increment = 0
                else:
                    increment = ms_per_measure / bar_length

                for note in part:
                    note_ms = self.current_ms
                    load_ms = note_ms - (self.distance / pixels_per_ms)
                    #Do not add blank notes otherwise lag
                    if note != '0':
                        play_note_list.append({'note': note, 'ms': note_ms, 'load_ms': load_ms, 'ppf': pixels_per_frame, 'index': index})
                        self.get_se_note(play_note_list, ms_per_measure, note, note_ms)
                        index += 1
                    if note in {'5', '6', '8'}:
                        play_note_list[-1]['color'] = 255
                    if note == '8' and play_note_list[-2]['note'] in ('7', '9'):
                        if balloon is None:
                            raise Exception("Balloon note found, but no count was specified")
                        if balloon_index >= len(balloon):
                            play_note_list[-1]['balloon'] = 0
                        else:
                            play_note_list[-1]['balloon'] = int(balloon[balloon_index])
                        balloon_index += 1
                    self.current_ms += increment

        # https://stackoverflow.com/questions/72899/how-to-sort-a-list-of-dictionaries-by-a-value-of-the-dictionary-in-python
        # Sorting by load_ms is necessary for drawing, as some notes appear on the
        # screen slower regardless of when they reach the judge circle
        # Bars can be sorted like this because they don't need hit detection
        draw_note_list = deque(sorted(play_note_list, key=lambda d: d['load_ms']))
        bar_list = deque(sorted(bar_list, key=lambda d: d['load_ms']))
        return play_note_list, draw_note_list, bar_list
