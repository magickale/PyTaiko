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
    selected_song: str = '' #Path
    textures: dict[str, list[ray.Texture]] = field(default_factory=lambda: dict())
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
        # Cache for rotated characters
        self._rotation_cache = {}
        # Cache for character measurements
        self._char_size_cache = {}
        self.texture = self._create_texture()

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
                          current_char.isspace() or
                          current_char in self.no_space_chars)

        # Additional check for capitalization transition
        if next_char and ((current_char.isupper() and next_char.islower()) or
                         next_char in self.no_space_chars):
            is_spacing_char = True

        # Apply spacing factor if it's a spacing character
        spacing = self.line_spacing * (self.lowercase_spacing_factor if is_spacing_char else 1.0)
        return self.font_size * spacing

    def _get_rotated_char(self, char, color):
        """Get or create a rotated character texture from cache"""
        cache_key = (char, color[0], color[1], color[2], color[3])

        if cache_key in self._rotation_cache:
            return self._rotation_cache[cache_key]

        char_size = self._get_char_size(char)

        # For rotated text, we need extra padding to prevent cutoff
        padding = max(int(self.font_size * 0.2), 2)  # Add padding proportional to font size
        temp_width = int(char_size.y) + padding * 2
        temp_height = int(char_size.x) + padding * 2

        # Create a temporary image with padding to ensure characters aren't cut off
        temp_image = ray.gen_image_color(temp_width, temp_height, ray.Color(0, 0, 0, 0))

        # Calculate centering offsets
        x_offset = padding
        y_offset = padding

        # Draw the character centered in the temporary image
        ray.image_draw_text_ex(
            temp_image,
            self.font,
            char,
            ray.Vector2(x_offset-5, y_offset),
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

    def _calculate_dimensions(self):
        """Calculate dimensions based on orientation"""
        if not self.vertical:
            # Horizontal text
            text_size = ray.measure_text_ex(self.font, self.text, self.font_size, 1.0)

            # Add extra padding to prevent cutoff
            extra_padding = max(int(self.font_size * 0.15), 2)
            width = int(text_size.x + self.outline_thickness * 4 + extra_padding * 2)
            height = int(text_size.y + self.outline_thickness * 4 + extra_padding * 2)
            padding_x = self.outline_thickness * 2 + extra_padding
            padding_y = self.outline_thickness * 2 + extra_padding

            return width, height, padding_x, padding_y
        else:
            # For vertical text, pre-calculate all character heights and widths
            char_heights = []
            char_widths = []

            for i, char in enumerate(self.text):
                next_char = self.text[i+1] if i+1 < len(self.text) else None
                char_heights.append(self._calculate_vertical_spacing(char, next_char))

                # For vertical characters, consider rotated dimensions
                if char in self.vertical_chars:
                    # Use padded width for rotated characters
                    padding = max(int(self.font_size * 0.2), 2) * 2
                    char_widths.append(self._get_char_size(char).x + padding)
                else:
                    char_widths.append(self._get_char_size(char).x)

            max_char_width = max(char_widths) if char_widths else 0
            total_height = sum(char_heights) if char_heights else 0

            # Add extra padding for vertical text
            extra_padding = max(int(self.font_size * 0.15), 2)
            width = int(max_char_width + self.outline_thickness * 4 + extra_padding * 2)
            height = int(total_height + self.outline_thickness * 4 + extra_padding * 2)
            padding_x = self.outline_thickness * 2 + extra_padding
            padding_y = self.outline_thickness * 2 + extra_padding

            return width, height, padding_x, padding_y

    def _draw_horizontal_text(self, image, padding_x, padding_y):
        """Draw horizontal text with outline"""
        # Draw outline
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

        # Draw main text
        ray.image_draw_text_ex(
            image,
            self.font,
            self.text,
            ray.Vector2(padding_x, padding_y),
            self.font_size,
            1.0,
            self.text_color
        )

    def _draw_vertical_text(self, image, width, padding_x, padding_y):
        """Draw vertical text with outline"""
        # Precalculate positions and spacings to avoid redundant calculations
        positions = []
        current_y = padding_y

        for i, char in enumerate(self.text):
            char_size = self._get_char_size(char)
            char_height = self._calculate_vertical_spacing(
                char,
                self.text[i+1] if i+1 < len(self.text) else None
            )

            # Calculate center position for each character
            if char in self.vertical_chars:
                # For vertical characters, we need to use the rotated image dimensions
                rotated_img = self._get_rotated_char(char, self.text_color)
                char_width = rotated_img.width
                center_offset = (width - char_width) // 2
            else:
                char_width = char_size.x
                center_offset = (width - char_width) // 2

            positions.append((char, center_offset, current_y, char_height, char in self.vertical_chars))
            current_y += char_height

        # First draw all outlines
        for dx in range(-self.outline_thickness, self.outline_thickness + 1):
            for dy in range(-self.outline_thickness, self.outline_thickness + 1):
                if dx == 0 and dy == 0:
                    continue

                for char, center_offset, y_pos, _, is_vertical in positions:
                    if is_vertical:
                        rotated_img = self._get_rotated_char(char, self.outline_color)
                        ray.image_draw(
                            image,
                            rotated_img,
                            ray.Rectangle(0, 0, rotated_img.width, rotated_img.height),
                            ray.Rectangle(
                                int(center_offset + dx),
                                int(y_pos + dy),
                                rotated_img.width,
                                rotated_img.height
                            ),
                            ray.WHITE
                        )
                    else:
                        ray.image_draw_text_ex(
                            image,
                            self.font,
                            char,
                            ray.Vector2(center_offset + dx, y_pos + dy),
                            self.font_size,
                            1.0,
                            self.outline_color
                        )

        # Then draw all main text
        for char, center_offset, y_pos, _, is_vertical in positions:
            if is_vertical:
                rotated_img = self._get_rotated_char(char, self.text_color)
                ray.image_draw(
                    image,
                    rotated_img,
                    ray.Rectangle(0, 0, rotated_img.width, rotated_img.height),
                    ray.Rectangle(
                        int(center_offset),
                        int(y_pos),
                        rotated_img.width,
                        rotated_img.height
                    ),
                    ray.WHITE
                )
            else:
                ray.image_draw_text_ex(
                    image,
                    self.font,
                    char,
                    ray.Vector2(center_offset, y_pos),
                    self.font_size,
                    1.0,
                    self.text_color
                )

    def _create_texture(self):
        """Create a texture with outlined text"""
        # Calculate dimensions
        width, height, padding_x, padding_y = self._calculate_dimensions()

        # Create transparent image
        image = ray.gen_image_color(width, height, ray.Color(0, 0, 0, 0))

        # Draw text based on orientation
        if not self.vertical:
            self._draw_horizontal_text(image, padding_x, padding_y)
        else:
            self._draw_vertical_text(image, width, padding_x, padding_y)

        # Create texture from image
        texture = ray.load_texture_from_image(image)
        ray.unload_image(image)
        return texture

    def draw(self, src: ray.Rectangle, dest: ray.Rectangle, origin: ray.Vector2, rotation: float, color: ray.Color):
        """Draw the outlined text"""
        ray.draw_texture_pro(self.texture, src, dest, origin, rotation, color)

    def unload(self):
        """Clean up resources"""
        # Unload all cached rotated images
        for img in self._rotation_cache.values():
            ray.unload_image(img)
        self._rotation_cache.clear()

        # Unload texture
        ray.unload_texture(self.texture)
