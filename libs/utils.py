import os
import tempfile
import time
import tomllib
import zipfile
from dataclasses import dataclass
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

def draw_scaled_texture(texture, x: int, y: int, scale: float, color: ray.Color) -> None:
    width = texture.width
    height = texture.height
    src_rect = ray.Rectangle(0, 0, width, height)
    dst_rect = ray.Rectangle(x, y, width*scale, height*scale)
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

    def __post_init__(self):
        self.texture = self._create_texture()

    def _create_texture(self):
        text_size = ray.measure_text_ex(self.font, self.text, self.font_size, 1.0)

        padding = self.outline_thickness * 2
        width = int(text_size.x + padding * 2)
        height = int(text_size.y + padding * 2)

        image = ray.gen_image_color(width, height, ray.Color(0, 0, 0, 0))

        for dx in range(-self.outline_thickness, self.outline_thickness + 1):
            for dy in range(-self.outline_thickness, self.outline_thickness + 1):
                if dx == 0 and dy == 0:
                    continue

                distance = (dx * dx + dy * dy) ** 0.5
                if distance <= self.outline_thickness:
                    ray.image_draw_text_ex(
                        image,
                        self.font,
                        self.text,
                        ray.Vector2(padding + dx, padding + dy),
                        self.font_size,
                        1.0,
                        self.outline_color
                    )

        ray.image_draw_text_ex(
            image,
            self.font,
            self.text,
            ray.Vector2(padding, padding),
            self.font_size,
            1.0,
            self.text_color
        )

        texture = ray.load_texture_from_image(image)

        ray.unload_image(image)

        return texture

    def draw(self, x: int, y: int, color: ray.Color):
        ray.draw_texture(self.texture, x, y, color)

    def unload(self):
        ray.unload_texture(self.texture)

'''
class RenderTextureStack:
    def __init__(self):
        """Initialize an empty stack for render textures."""
        self.texture_stack = []

    def load_render_texture(self, width, height):
        """Create and return a render texture with the specified dimensions."""
        return ray.load_render_texture(width, height)

    def begin_texture_mode(self, target):
        """Begin drawing to the render texture and add it to the stack."""
        ray.begin_texture_mode(target)
        self.texture_stack.append(target)
        return target

    def end_texture_mode(self, pop_count=1):
        """End the texture mode for the specified number of textures in the stack."""
        if not self.texture_stack:
            raise IndexError("Cannot end texture mode: texture stack is empty")

        # Ensure pop_count is within valid range
        pop_count = min(pop_count, len(self.texture_stack))

        # End the texture modes and pop from stack
        for _ in range(pop_count):
            ray.end_texture_mode()
            self.texture_stack.pop()

    def get_texture(self, target):
        """Get the texture from the render texture."""
        return ray.get_texture_default(target)

    def draw_texture(self, texture, pos_x, pos_y, tint=ray.WHITE):
        """Draw a texture at the specified position with the given tint."""
        ray.draw_texture(texture, pos_x, pos_y, tint)

    def get_current_target(self):
        """Get the current active render target from the stack."""
        if not self.texture_stack:
            return None
        return self.texture_stack[-1]

render_stack = RenderTextureStack()
'''
