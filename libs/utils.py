import os
import tempfile
import time
import tomllib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyray as ray

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

def get_pixels_per_frame(bpm: float, time_signature: float, distance: float) -> float:
    beat_duration = 60 / bpm
    total_time = time_signature * beat_duration
    total_frames = 60 * total_time
    return (distance / total_frames)

def get_config() -> dict[str, Any]:
    with open('config.toml', "rb") as f:
        config_file = tomllib.load(f)
    return config_file

def draw_scaled_texture(texture: ray.Texture, x: int, y: int, scale: float, color: ray.Color) -> None:
    src_rect = ray.Rectangle(0, 0, texture.width, texture.height)
    dst_rect = ray.Rectangle(x, y, texture.width*scale, texture.height*scale)
    ray.draw_texture_pro(texture, src_rect, dst_rect, ray.Vector2(0, 0), 0, color)

@dataclass
class SessionData:
    selected_song: str = '' #Path
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
    songs_played: int = 0

global_data = GlobalData()

@dataclass
class OutlinedText:
    font: ray.Font
    text: str
    font_size: int
    text_color: ray.Color
    outline_color: ray.Color
    outline_thickness: int = 2
    vertical: bool = False
    line_spacing: float = 1.0  # Line spacing for vertical text
    lowercase_spacing_factor: float = 0.85  # Adjust spacing for lowercase letters and whitespace
    vertical_chars: set = field(default_factory=lambda: {'-', '|', '/', '\\', 'ー'})
    no_space_chars: set = field(default_factory=lambda: {
        'ぁ', 'ア','ぃ', 'イ','ぅ', 'ウ','ぇ', 'エ','ぉ', 'オ',
        'ゃ', 'ャ','ゅ', 'ュ','ょ', 'ョ','っ', 'ッ','ゎ', 'ヮ',
        'ヶ', 'ヵ','ㇰ','ㇱ','ㇲ','ㇳ','ㇴ','ㇵ','ㇶ','ㇷ','ㇸ',
        'ㇹ','ㇺ','ㇻ','ㇼ','ㇽ','ㇾ','ㇿ'
    })

    def __post_init__(self):
        self.texture = self._create_texture()

    def _calculate_vertical_spacing(self, current_char, next_char=None):
        # Check if current char is lowercase or whitespace
        is_spacing_char = current_char.islower() or current_char.isspace() or current_char in self.no_space_chars

        # Additional check for capitalization transition
        if next_char and current_char.isupper() and next_char.islower() or next_char in self.no_space_chars:
            is_spacing_char = True

        # Apply spacing factor if it's a spacing character
        if is_spacing_char:
            return self.font_size * (self.line_spacing * self.lowercase_spacing_factor)
        return self.font_size * self.line_spacing

    def _draw_rotated_char(self, image, font, char, pos, font_size, color, is_outline=False):
        # Calculate character size
        char_size = ray.measure_text_ex(font, char, font_size, 1.0)

        # Create a temporary image for the rotated character
        temp_image = ray.gen_image_color(int(char_size.y), int(char_size.x), ray.Color(0, 0, 0, 0))

        # Draw the character on the temporary image
        ray.image_draw_text_ex(
            temp_image,
            font,
            char,
            ray.Vector2(0, 0),
            font_size,
            1.0,
            color
        )

        # Rotate the temporary image 90 degrees
        rotated_image = ray.gen_image_color(int(char_size.x), int(char_size.y), ray.Color(0, 0, 0, 0))
        for x in range(int(char_size.y)):
            for y in range(int(char_size.x)):
                pixel = ray.get_image_color(temp_image, y, int(char_size.y) - x - 1)
                ray.image_draw_pixel(
                    rotated_image,
                    x,
                    y,
                    pixel
                )

        # Unload temporary image
        ray.unload_image(temp_image)

        # Draw the rotated image
        ray.image_draw(
            image,
            rotated_image,
            ray.Rectangle(0, 0, rotated_image.width, rotated_image.height),
            ray.Rectangle(int(pos.x), int(pos.y), rotated_image.width, rotated_image.height),
            ray.WHITE
        )

        # Unload rotated image
        ray.unload_image(rotated_image)

    def _create_texture(self):
        # Measure text size
        text_size = ray.measure_text_ex(self.font, self.text, self.font_size, 1.0)

        # Determine dimensions based on orientation
        if not self.vertical:
            width = int(text_size.x + self.outline_thickness * 4)
            height = int(text_size.y + self.outline_thickness * 4)
            padding_x, padding_y = self.outline_thickness * 2, self.outline_thickness * 2
        else:
            # For vertical text, calculate total height and max character width
            char_heights = [
                self._calculate_vertical_spacing(
                    self.text[i],
                    self.text[i+1] if i+1 < len(self.text) else None
                )
                for i in range(len(self.text))
            ]

            # Calculate the maximum character width (including outline)
            char_widths = []
            for char in self.text:
                if char in self.vertical_chars:
                    # For vertically drawn characters, use font size as width
                    char_width = self.font_size
                else:
                    # Normal character width
                    char_width = ray.measure_text_ex(self.font, char, self.font_size, 1.0).x
                char_widths.append(char_width)

            max_char_width = max(char_widths) if char_widths else 0
            total_height = sum(char_heights) if char_heights else 0

            # Adjust dimensions to be tighter around the text
            width = int(max_char_width + self.outline_thickness * 2)  # Reduced padding
            height = int(total_height + self.outline_thickness * 2)   # Reduced padding
            padding_x = self.outline_thickness
            padding_y = self.outline_thickness

        # Create transparent image
        image = ray.gen_image_color(width, height, ray.Color(0, 0, 0, 0))

        # Draw outline
        if not self.vertical:
            # Horizontal text outline
            for dx in range(-self.outline_thickness, self.outline_thickness + 1):
                for dy in range(-self.outline_thickness, self.outline_thickness + 1):
                    if dx == 0 and dy == 0:
                        continue
                    ray.image_draw_text_ex(
                        image,
                        self.font,
                        self.text,
                        ray.Vector2(padding_x + dx, padding_y + dy),
                        self.font_size,
                        1.0,
                        self.outline_color
                    )
        else:
            # Vertical text outline
            current_y = padding_y
            for dx in range(-self.outline_thickness, self.outline_thickness + 1):
                for dy in range(-self.outline_thickness, self.outline_thickness + 1):
                    if dx == 0 and dy == 0:
                        continue

                    current_y = padding_y
                    for i, char in enumerate(self.text):
                        if char in self.vertical_chars:
                            char_width = self.font_size
                        else:
                            char_width = ray.measure_text_ex(self.font, char, self.font_size, 1.0).x

                        # Calculate centered position
                        center_offset = (width - char_width) // 2
                        char_height = self._calculate_vertical_spacing(
                            char,
                            self.text[i+1] if i+1 < len(self.text) else None
                        )

                        if char in self.vertical_chars:
                            self._draw_rotated_char(
                                image,
                                self.font,
                                char,
                                ray.Vector2(
                                    center_offset + dx,
                                    current_y + dy
                                ),
                                self.font_size,
                                self.outline_color,
                                is_outline=True
                            )
                        else:
                            ray.image_draw_text_ex(
                                image,
                                self.font,
                                char,
                                ray.Vector2(center_offset + dx, current_y + dy),
                                self.font_size,
                                1.0,
                                self.outline_color
                            )

                        current_y += char_height

        # Draw main text
        if not self.vertical:
            # Horizontal text
            ray.image_draw_text_ex(
                image,
                self.font,
                self.text,
                ray.Vector2(padding_x, padding_y),
                self.font_size,
                1.0,
                self.text_color
            )
        else:
            # Vertical text
            current_y = padding_y
            for i, char in enumerate(self.text):
                if char in self.vertical_chars:
                    char_width = self.font_size
                else:
                    char_width = ray.measure_text_ex(self.font, char, self.font_size, 1.0).x

                # Calculate centered position
                center_offset = (width - char_width) // 2
                char_height = self._calculate_vertical_spacing(
                    char,
                    self.text[i+1] if i+1 < len(self.text) else None
                )

                if char in self.vertical_chars:
                    self._draw_rotated_char(
                        image,
                        self.font,
                        char,
                        ray.Vector2(
                            center_offset,
                            current_y
                        ),
                        self.font_size,
                        self.text_color
                    )
                else:
                    ray.image_draw_text_ex(
                        image,
                        self.font,
                        char,
                        ray.Vector2(center_offset, current_y),
                        self.font_size,
                        1.0,
                        self.text_color
                    )

                current_y += char_height

        # Create texture and clean up
        texture = ray.load_texture_from_image(image)
        ray.unload_image(image)
        return texture

    def draw(self, src: ray.Rectangle, dest: ray.Rectangle, origin: ray.Vector2, rotation: float, color: ray.Color):
        ray.draw_texture_pro(self.texture, src, dest, origin, rotation, color)

    def unload(self):
        ray.unload_texture(self.texture)
