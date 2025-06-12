import hashlib
import math
import os
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pyray as ray
import tomlkit

#TJA Format creator is unknown. I did not create the format, but I did write the parser though.

def get_zip_filenames(zip_path: Path) -> list[str]:
    result = []
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        for file_name in file_list:
            result.append(file_name)
    return result

def load_image_from_zip(zip_path: Path, filename: str) -> ray.Image:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        with zip_ref.open(filename) as image_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(image_file.read())
                temp_file_path = temp_file.name
        image = ray.load_image(temp_file_path)
        os.remove(temp_file_path)
        return image

def load_texture_from_zip(zip_path: Path, filename: str) -> ray.Texture:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        with zip_ref.open(filename) as image_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(image_file.read())
                temp_file_path = temp_file.name
        texture = ray.load_texture(temp_file_path)
        os.remove(temp_file_path)
        return texture

def load_all_textures_from_zip(zip_path: Path) -> dict[str, list[ray.Texture]]:
    result_dict = dict()
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        files = zip_ref.namelist()
        for file in files:
            with zip_ref.open(file) as image_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(image_file.read())
                    temp_file_path = temp_file.name
            texture = ray.load_texture(temp_file_path)
            os.remove(temp_file_path)

            true_filename, index = file.split('_img')
            index = int(index.split('.')[0])
            if true_filename not in result_dict:
                result_dict[true_filename] = []
            while len(result_dict[true_filename]) <= index:
                result_dict[true_filename].append(None)
            result_dict[true_filename][index] = texture
    return result_dict


def rounded(num: float) -> int:
    sign = 1 if (num >= 0) else -1
    num = abs(num)
    result = int(num)
    if (num - result >= 0.5):
        result += 1
    return sign * result

def get_current_ms() -> int:
    return rounded(time.time() * 1000)

def strip_comments(code: str) -> str:
    result = ''
    index = 0
    for line in code.splitlines():
        comment_index = line.find('//')
        if comment_index == -1:
            result += line
        elif comment_index != 0 and not line[:comment_index].isspace():
            result += line[:comment_index]
        index += 1
    return result

@lru_cache
def get_pixels_per_frame(bpm: float, time_signature: float, distance: float) -> float:
    if bpm == 0:
        return 0
    beat_duration = 60 / bpm
    total_time = time_signature * beat_duration
    total_frames = 60 * total_time
    return (distance / total_frames)

def get_config() -> dict[str, Any]:
    with open('config.toml', "r", encoding="utf-8") as f:
        config_file = tomlkit.load(f)
    return config_file

def save_config(config: dict[str, Any]) -> None:
    with open('config.toml', "w", encoding="utf-8") as f:
        tomlkit.dump(config, f)

def is_l_don_pressed() -> bool:
    keys = global_data.config["keybinds"]["left_don"]
    for key in keys:
        if ray.is_key_pressed(ord(key)):
            return True

    if ray.is_gamepad_available(0):
        if ray.is_gamepad_button_pressed(0, 16):
            return True

    mid_x, mid_y = (1280//2, 720)
    allowed_gestures = {ray.Gesture.GESTURE_TAP, ray.Gesture.GESTURE_DOUBLETAP}
    if ray.get_gesture_detected() in allowed_gestures and ray.is_gesture_detected(ray.get_gesture_detected()):
        for i in range(min(ray.get_touch_point_count(), 10)):
            tap_pos = (ray.get_touch_position(i).x, ray.get_touch_position(i).y)
            if math.dist(tap_pos, (mid_x, mid_y)) < 300 and tap_pos[0] <= mid_x:
                return True

    return False

def is_r_don_pressed() -> bool:
    keys = global_data.config["keybinds"]["right_don"]
    for key in keys:
        if ray.is_key_pressed(ord(key)):
            return True

    if ray.is_gamepad_available(0):
        if ray.is_gamepad_button_pressed(0, 17):
            return True

    mid_x, mid_y = (1280//2, 720)
    allowed_gestures = {ray.Gesture.GESTURE_TAP, ray.Gesture.GESTURE_DOUBLETAP}
    if ray.get_gesture_detected() in allowed_gestures and ray.is_gesture_detected(ray.get_gesture_detected()):
        for i in range(min(ray.get_touch_point_count(), 10)):
            tap_pos = (ray.get_touch_position(i).x, ray.get_touch_position(i).y)
            if math.dist(tap_pos, (mid_x, mid_y)) < 300 and tap_pos[0] > mid_x:
                return True

    return False

def is_l_kat_pressed() -> bool:
    keys = global_data.config["keybinds"]["left_kat"]
    for key in keys:
        if ray.is_key_pressed(ord(key)):
            return True

    if ray.is_gamepad_available(0):
        if ray.is_gamepad_button_pressed(0, 10):
            return True

    mid_x, mid_y = (1280//2, 720)
    allowed_gestures = {ray.Gesture.GESTURE_TAP, ray.Gesture.GESTURE_DOUBLETAP}
    if ray.get_gesture_detected() in allowed_gestures and ray.is_gesture_detected(ray.get_gesture_detected()):
        for i in range(min(ray.get_touch_point_count(), 10)):
            tap_pos = (ray.get_touch_position(i).x, ray.get_touch_position(i).y)
            if math.dist(tap_pos, (mid_x, mid_y)) >= 300 and tap_pos[0] <= mid_x:
                return True

    return False

def is_r_kat_pressed() -> bool:
    keys = global_data.config["keybinds"]["right_kat"]
    for key in keys:
        if ray.is_key_pressed(ord(key)):
            return True

    if ray.is_gamepad_available(0):
        if ray.is_gamepad_button_pressed(0, 12):
            return True

    mid_x, mid_y = (1280//2, 720)
    allowed_gestures = {ray.Gesture.GESTURE_TAP, ray.Gesture.GESTURE_DOUBLETAP}
    if ray.get_gesture_detected() in allowed_gestures and ray.is_gesture_detected(ray.get_gesture_detected()):
        for i in range(min(ray.get_touch_point_count(), 10)):
            tap_pos = (ray.get_touch_position(i).x, ray.get_touch_position(i).y)
            if math.dist(tap_pos, (mid_x, mid_y)) >= 300 and tap_pos[0] > mid_x:
                return True

    return False

def draw_scaled_texture(texture: ray.Texture, x: int, y: int, scale: float, color: ray.Color) -> None:
    src_rect = ray.Rectangle(0, 0, texture.width, texture.height)
    dst_rect = ray.Rectangle(x, y, texture.width*scale, texture.height*scale)
    ray.draw_texture_pro(texture, src_rect, dst_rect, ray.Vector2(0, 0), 0, color)

@dataclass
class SessionData:
    selected_difficulty: int = 0
    song_title: str = ''
    result_score: int = 0
    result_good: int = 0
    result_ok: int = 0
    result_bad: int = 0
    result_max_combo: int = 0
    result_total_drumroll: int = 0
    result_gauge_length: int = 0

session_data = SessionData()

def reset_session():
    return SessionData()

@dataclass
class GlobalData:
    selected_song: Path = Path()
    textures: dict[str, list[ray.Texture]] = field(default_factory=lambda: dict())
    songs_played: int = 0
    config: dict = field(default_factory=lambda: dict())

global_data = GlobalData()

rotation_cache = dict()
char_size_cache = dict()
horizontal_cache = dict()
text_cache = set()
if not Path('cache/image').exists():
    Path('cache').mkdir()
    Path('cache/image').mkdir()
for file in Path('cache/image').iterdir():
    text_cache.add(file.stem)

@dataclass
class OutlinedText:
    text: str
    font_size: int
    text_color: ray.Color
    outline_color: ray.Color
    font: ray.Font = ray.Font()
    outline_thickness: int = 2
    vertical: bool = False
    line_spacing: float = 1.0  # Line spacing for vertical text
    horizontal_spacing: float = 1.0  # Character spacing for horizontal text
    lowercase_spacing_factor: float = 0.85  # Adjust spacing for lowercase letters and whitespace
    vertical_chars: set = field(default_factory=lambda: {'-', '‐', '|', '/', '\\', 'ー', '～', '~', '（', '）', '(', ')',
                                                        '「', '」', '[', ']', '［', '］', '【', '】', '…', '→', '→', ':', '：'})
    no_space_chars: set = field(default_factory=lambda: {
        'ぁ', 'ア','ぃ', 'イ','ぅ', 'ウ','ぇ', 'エ','ぉ', 'オ',
        'ゃ', 'ャ','ゅ', 'ュ','ょ', 'ョ','っ', 'ッ','ゎ', 'ヮ',
        'ヶ', 'ヵ','ㇰ','ㇱ','ㇲ','ㇳ','ㇴ','ㇵ','ㇶ','ㇷ','ㇸ',
        'ㇹ','ㇺ','ㇻ','ㇼ','ㇽ','ㇾ','ㇿ'
    })
    # New field for horizontal exception strings
    horizontal_exceptions: set = field(default_factory=lambda: {'!!!!', '!!!', '!!', '！！','！！！','!?', '！？', '??', '？？', '†††', '(°∀°)', '(°∀°)'})
    # New field for adjacent punctuation characters
    adjacent_punctuation: set = field(default_factory=lambda: {'.', ',', '。', '、', "'", '"', '´', '`'})

    def __post_init__(self):
        # Cache for rotated characters
        self._rotation_cache = rotation_cache
        # Cache for character measurements
        self._char_size_cache = char_size_cache
        # Cache for horizontal exception measurements
        self._horizontal_cache = horizontal_cache
        self.hash = self._get_hash()
        self.texture = self._create_texture()

    def _load_font_for_text(self, text: str) -> ray.Font:
        codepoint_count = ray.ffi.new('int *', 0)
        unique_codepoints = set(text)
        codepoints = ray.load_codepoints(''.join(unique_codepoints), codepoint_count)
        return ray.load_font_ex(str(Path('Graphics/Modified-DFPKanteiryu-XB.ttf')), self.font_size, codepoints, 0)

    def _get_hash(self):
        n = hashlib.sha256()
        n.update(self.text.encode('utf-8'))
        n.update(str(self.vertical).encode('utf-8'))
        n.update(str(self.horizontal_spacing).encode('utf-8'))  # Include horizontal spacing in hash
        n.update(str(self.outline_color.a).encode('utf-8'))
        n.update(str(self.outline_color.r).encode('utf-8'))
        n.update(str(self.outline_color.g).encode('utf-8'))
        n.update(str(self.outline_color.b).encode('utf-8'))
        n.update(str(self.text_color.a).encode('utf-8'))
        n.update(str(self.text_color.r).encode('utf-8'))
        n.update(str(self.text_color.g).encode('utf-8'))
        n.update(str(self.text_color.b).encode('utf-8'))
        n.update(str(self.font_size).encode('utf-8'))
        return n.hexdigest()

    def _parse_text_segments(self):
        """Parse text into segments, identifying horizontal exceptions"""
        if not self.vertical:
            return [{'text': self.text, 'is_horizontal': False}]

        segments = []
        i = 0
        current_segment = ""

        while i < len(self.text):
            # Check if any horizontal exception starts at current position
            found_exception = None
            for exception in self.horizontal_exceptions:
                if self.text[i:].startswith(exception):
                    found_exception = exception
                    break

            if found_exception:
                # Save current segment if it exists
                if current_segment:
                    segments.append({'text': current_segment, 'is_horizontal': False})
                    current_segment = ""

                # Add horizontal exception as separate segment
                segments.append({'text': found_exception, 'is_horizontal': True})
                i += len(found_exception)
            else:
                # Add character to current segment
                current_segment += self.text[i]
                i += 1

        # Add remaining segment
        if current_segment:
            segments.append({'text': current_segment, 'is_horizontal': False})

        return segments

    def _group_characters_with_punctuation(self, text):
        """Group characters with their adjacent punctuation"""
        groups = []
        i = 0

        while i < len(text):
            current_char = text[i]
            group = {'main_char': current_char, 'adjacent_punct': []}

            # Look ahead for adjacent punctuation
            j = i + 1
            while j < len(text) and text[j] in self.adjacent_punctuation:
                group['adjacent_punct'].append(text[j])
                j += 1

            groups.append(group)
            i = j  # Move to next non-punctuation character

        return groups

    def _get_horizontal_exception_texture(self, text: str, color):
        """Get or create a texture for horizontal exception text"""
        cache_key = (text, color.r, color.g, color.b, color.a, 'horizontal')

        if cache_key in self._horizontal_cache:
            return self._horizontal_cache[cache_key]

        # Measure the text
        text_size = ray.measure_text_ex(self.font, text, self.font_size, 1.0)
        padding = int(self.outline_thickness * 3)

        # Create image with proper dimensions
        img_width = int(text_size.x + padding * 2)
        img_height = int(text_size.y + padding * 2)
        temp_image = ray.gen_image_color(img_width, img_height, ray.Color(0, 0, 0, 0))

        # Draw the text centered
        ray.image_draw_text_ex(
            temp_image,
            self.font,
            text,
            ray.Vector2(padding, padding),
            self.font_size,
            1.0,
            color
        )

        # Cache the image
        self._horizontal_cache[cache_key] = temp_image
        return temp_image

    def _get_char_size(self, char):
        """Cache character size measurements"""
        if char not in self._char_size_cache:
            if char in self.vertical_chars:
                # For vertical chars, width and height are swapped
                self._char_size_cache[char] = ray.Vector2(self.font_size, self.font_size)
            else:
                self._char_size_cache[char] = ray.measure_text_ex(self.font, char, self.font_size, 1.0)
        return self._char_size_cache[char]

    def _calculate_vertical_spacing(self, current_char, next_char=None):
        """Calculate vertical spacing between characters"""
        # Check if current char is lowercase, whitespace or a special character
        is_spacing_char = (current_char.islower() or
                          current_char.isspace())

        # Additional check for capitalization transition
        if next_char and ((current_char.isupper() and next_char.islower()) or
                         next_char in self.no_space_chars):
            is_spacing_char = True

        # Apply spacing factor if it's a spacing character
        spacing = self.line_spacing * (self.lowercase_spacing_factor if is_spacing_char else 1.0)
        return self.font_size * spacing

    def _get_rotated_char(self, char: str, color):
        """Get or create a rotated character texture from cache"""
        cache_key = (char, color.r, color.g, color.b, color.a)

        if cache_key in self._rotation_cache:
            return self._rotation_cache[cache_key]

        char_size = self._get_char_size(char)
        padding = int(self.outline_thickness * 3)  # Increased padding
        temp_width = max(int(char_size.y) + padding, self.font_size + padding)
        temp_height = max(int(char_size.x) + padding, self.font_size + padding)
        temp_image = ray.gen_image_color(temp_width, temp_height, ray.Color(0, 0, 0, 0))

        center_x = (temp_width - char_size.y) // 2
        center_y = (temp_height - char_size.x) // 2

        ray.image_draw_text_ex(
            temp_image,
            self.font,
            char,
            ray.Vector2(center_x-5, center_y),  # Centered placement with padding
            self.font_size,
            1.0,
            color
        )

        # Rotate the temporary image 90 degrees counterclockwise
        rotated_image = ray.gen_image_color(temp_height, temp_width, ray.Color(0, 0, 0, 0))
        for x in range(temp_width):
            for y in range(temp_height):
                pixel = ray.get_image_color(temp_image, x, temp_height - y - 1)
                ray.image_draw_pixel(rotated_image, y, x, pixel)

        # Unload temporary image
        ray.unload_image(temp_image)

        # Cache the rotated image
        self._rotation_cache[cache_key] = rotated_image
        return rotated_image

    def _calculate_horizontal_text_width(self):
        """Calculate the total width of horizontal text with custom spacing"""
        if not self.text:
            return 0

        total_width = 0
        for i, char in enumerate(self.text):
            char_size = ray.measure_text_ex(self.font, char, self.font_size, 1.0)
            total_width += char_size.x

            # Add spacing between characters (except for the last character)
            if i < len(self.text) - 1:
                total_width += (char_size.x * (self.horizontal_spacing - 1.0))

        return total_width

    def _calculate_dimensions(self):
        padding = int(self.outline_thickness * 3)

        if not self.vertical:
            if self.horizontal_spacing == 1.0:
                # Use default raylib measurement for normal spacing
                text_size = ray.measure_text_ex(self.font, self.text, self.font_size, 1.0)
                return int(text_size.x + padding * 2), int(text_size.y + padding * 2)
            else:
                # Calculate custom spacing width
                text_width = self._calculate_horizontal_text_width()
                text_height = ray.measure_text_ex(self.font, "Ag", self.font_size, 1.0).y  # Use sample chars for height
                return int(text_width + padding * 2), int(text_height + padding * 2)
        else:
            # Parse text into segments
            segments = self._parse_text_segments()

            char_heights = []
            char_widths = []

            for segment in segments:
                if segment['is_horizontal']:
                    # For horizontal exceptions, add their height as spacing
                    text_size = ray.measure_text_ex(self.font, segment['text'], self.font_size, 1.0)
                    char_heights.append(text_size.y * self.line_spacing)
                    char_widths.append(text_size.x)
                else:
                    # Process vertical text with character grouping
                    char_groups = self._group_characters_with_punctuation(segment['text'])

                    for i, group in enumerate(char_groups):
                        main_char = group['main_char']
                        adjacent_punct = group['adjacent_punct']

                        # Get next group's main character for spacing calculation
                        next_char = char_groups[i+1]['main_char'] if i+1 < len(char_groups) else None
                        char_heights.append(self._calculate_vertical_spacing(main_char, next_char))

                        # Calculate width considering main char + adjacent punctuation
                        main_char_size = self._get_char_size(main_char)
                        group_width = main_char_size.x

                        # Add width for adjacent punctuation
                        for punct in adjacent_punct:
                            punct_size = self._get_char_size(punct)
                            group_width += punct_size.x

                        # For vertical characters, consider rotated dimensions
                        if main_char in self.vertical_chars:
                            char_widths.append(group_width + padding)
                        else:
                            char_widths.append(group_width)

            max_char_width = max(char_widths) if char_widths else 0
            total_height = sum(char_heights) if char_heights else 0

            width = int(max_char_width + padding * 2)  # Padding on both sides
            height = int(total_height + padding * 2)   # Padding on top and bottom

            return width, height

    def _draw_horizontal_text(self, image):
        if self.horizontal_spacing == 1.0:
            # Use original method for normal spacing
            text_size = ray.measure_text_ex(self.font, self.text, self.font_size, 1.0)
            position = ray.Vector2((image.width - text_size.x) / 2, (image.height - text_size.y) / 2)

            for dx in range(-self.outline_thickness, self.outline_thickness + 1):
                for dy in range(-self.outline_thickness, self.outline_thickness + 1):
                    # Skip the center position (will be drawn as main text)
                    if dx == 0 and dy == 0:
                        continue

                    # Calculate outline distance
                    dist = (dx*dx + dy*dy) ** 0.5

                    # Only draw outline positions that are near the outline thickness
                    if dist <= self.outline_thickness + 0.5:
                        ray.image_draw_text_ex(
                            image,
                            self.font,
                            self.text,
                            ray.Vector2(position.x + dx, position.y + dy),
                            self.font_size,
                            1.0,
                            self.outline_color
                        )

            # Draw main text
            ray.image_draw_text_ex(
                image,
                self.font,
                self.text,
                position,
                self.font_size,
                1.0,
                self.text_color
            )
        else:
            # Draw text with custom character spacing
            text_width = self._calculate_horizontal_text_width()
            text_height = ray.measure_text_ex(self.font, "Ag", self.font_size, 1.0).y

            start_x = (image.width - text_width) / 2
            start_y = (image.height - text_height) / 2

            # First draw all outlines
            current_x = start_x
            for i, char in enumerate(self.text):
                char_size = ray.measure_text_ex(self.font, char, self.font_size, 1.0)

                for dx in range(-self.outline_thickness, self.outline_thickness + 1):
                    for dy in range(-self.outline_thickness, self.outline_thickness + 1):
                        if dx == 0 and dy == 0:
                            continue

                        dist = (dx*dx + dy*dy) ** 0.5
                        if dist <= self.outline_thickness + 0.5:
                            ray.image_draw_text_ex(
                                image,
                                self.font,
                                char,
                                ray.Vector2(current_x + dx, start_y + dy),
                                self.font_size,
                                1.0,
                                self.outline_color
                            )

                # Move to next character position
                current_x += char_size.x
                if i < len(self.text) - 1:  # Add spacing except for last character
                    current_x += (char_size.x * (self.horizontal_spacing - 1.0))

            # Then draw all main text
            current_x = start_x
            for i, char in enumerate(self.text):
                char_size = ray.measure_text_ex(self.font, char, self.font_size, 1.0)

                ray.image_draw_text_ex(
                    image,
                    self.font,
                    char,
                    ray.Vector2(current_x, start_y),
                    self.font_size,
                    1.0,
                    self.text_color
                )

                # Move to next character position
                current_x += char_size.x
                if i < len(self.text) - 1:  # Add spacing except for last character
                    current_x += (char_size.x * (self.horizontal_spacing - 1.0))

    def _draw_vertical_text(self, image, width):
        padding = int(self.outline_thickness * 2)
        segments = self._parse_text_segments()

        positions = []
        current_y = padding  # Start with padding at the top

        for segment in segments:
            if segment['is_horizontal']:
                # Handle horizontal exception
                text_size = ray.measure_text_ex(self.font, segment['text'], self.font_size, 1.0)
                center_offset = (width - text_size.x) // 2
                char_height = text_size.y * self.line_spacing

                positions.append({
                    'type': 'horizontal',
                    'text': segment['text'],
                    'x': center_offset,
                    'y': current_y,
                    'height': char_height
                })
                current_y += char_height
            else:
                # Handle vertical text with character grouping
                char_groups = self._group_characters_with_punctuation(segment['text'])

                for i, group in enumerate(char_groups):
                    main_char = group['main_char']
                    adjacent_punct = group['adjacent_punct']

                    # Get next group for spacing calculation
                    next_char = char_groups[i+1]['main_char'] if i+1 < len(char_groups) else None
                    char_height = self._calculate_vertical_spacing(main_char, next_char)

                    # Calculate positioning for main character
                    main_char_size = self._get_char_size(main_char)

                    if main_char in self.vertical_chars:
                        rotated_img = self._get_rotated_char(main_char, self.text_color)
                        main_char_width = rotated_img.width
                        center_offset = (width - main_char_width) // 2
                    else:
                        main_char_width = main_char_size.x
                        center_offset = (width - main_char_width) // 2

                    # Add main character position
                    positions.append({
                        'type': 'vertical',
                        'char': main_char,
                        'x': center_offset,
                        'y': current_y,
                        'height': char_height,
                        'is_vertical_char': main_char in self.vertical_chars
                    })

                    # Add adjacent punctuation positions
                    punct_x_offset = center_offset + main_char_width
                    for punct in adjacent_punct:
                        punct_size = self._get_char_size(punct)

                        positions.append({
                            'type': 'vertical',
                            'char': punct,
                            'x': punct_x_offset,
                            'y': current_y+5,
                            'height': 0,  # No additional height for punctuation
                            'is_vertical_char': punct in self.vertical_chars,
                            'is_adjacent': True
                        })

                        punct_x_offset += punct_size.x

                    current_y += char_height

        # First draw all outlines
        outline_thickness = int(self.outline_thickness)

        for pos in positions:
            if pos['type'] == 'horizontal':
                # Draw horizontal text outline
                for dx in range(-outline_thickness, outline_thickness + 1):
                    for dy in range(-outline_thickness, outline_thickness + 1):
                        if dx == 0 and dy == 0:
                            continue

                        dist = (dx*dx + dy*dy) ** 0.5
                        if dist <= outline_thickness + 0.5:
                            ray.image_draw_text_ex(
                                image,
                                self.font,
                                pos['text'],
                                ray.Vector2(pos['x'] + dx, pos['y'] + dy),
                                self.font_size,
                                1.0,
                                self.outline_color
                            )
            else:
                # Draw vertical character outline
                for dx in range(-outline_thickness, outline_thickness + 1):
                    for dy in range(-outline_thickness, outline_thickness + 1):
                        if dx == 0 and dy == 0:
                            continue

                        dist = (dx*dx + dy*dy) ** 0.5
                        if dist <= outline_thickness + 0.5:
                            if pos['is_vertical_char']:
                                rotated_img = self._get_rotated_char(pos['char'], self.outline_color)
                                ray.image_draw(
                                    image,
                                    rotated_img,
                                    ray.Rectangle(0, 0, rotated_img.width, rotated_img.height),
                                    ray.Rectangle(
                                        int(pos['x'] + dx),
                                        int(pos['y'] + dy),
                                        rotated_img.width,
                                        rotated_img.height
                                    ),
                                    ray.WHITE
                                )
                            else:
                                ray.image_draw_text_ex(
                                    image,
                                    self.font,
                                    pos['char'],
                                    ray.Vector2(pos['x'] + dx, pos['y'] + dy),
                                    self.font_size,
                                    1.0,
                                    self.outline_color
                                )

        # Then draw all main text
        for pos in positions:
            if pos['type'] == 'horizontal':
                # Draw horizontal text
                ray.image_draw_text_ex(
                    image,
                    self.font,
                    pos['text'],
                    ray.Vector2(pos['x'], pos['y']),
                    self.font_size,
                    1.0,
                    self.text_color
                )
            else:
                # Draw vertical character
                if pos['is_vertical_char']:
                    rotated_img = self._get_rotated_char(pos['char'], self.text_color)
                    ray.image_draw(
                        image,
                        rotated_img,
                        ray.Rectangle(0, 0, rotated_img.width, rotated_img.height),
                        ray.Rectangle(
                            int(pos['x']),
                            int(pos['y']),
                            rotated_img.width,
                            rotated_img.height
                        ),
                        ray.WHITE
                    )
                else:
                    ray.image_draw_text_ex(
                        image,
                        self.font,
                        pos['char'],
                        ray.Vector2(pos['x'], pos['y']),
                        self.font_size,
                        1.0,
                        self.text_color
                    )

    def _create_texture(self):
        if self.hash in text_cache:
            texture = ray.load_texture(f'cache/image/{self.hash}.png')
            return texture

        self.font = self._load_font_for_text(self.text)

        width, height = self._calculate_dimensions()

        width += int(self.outline_thickness * 1.5)
        height += int(self.outline_thickness * 1.5)

        image = ray.gen_image_color(width, height, ray.Color(0, 0, 0, 0))

        if not self.vertical:
            self._draw_horizontal_text(image)
        else:
            self._draw_vertical_text(image, width)

        ray.export_image(image, f'cache/image/{self.hash}.png')
        texture = ray.load_texture_from_image(image)
        ray.unload_image(image)
        return texture

    def draw(self, src: ray.Rectangle, dest: ray.Rectangle, origin: ray.Vector2, rotation: float, color: ray.Color):
        ray.draw_texture_pro(self.texture, src, dest, origin, rotation, color)

    def unload(self):
        for img in self._rotation_cache.values():
            ray.unload_image(img)
        self._rotation_cache.clear()

        for img in self._horizontal_cache.values():
            ray.unload_image(img)
        self._horizontal_cache.clear()

        ray.unload_texture(self.texture)
