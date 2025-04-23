import os
import tempfile
import time
import zipfile
from dataclasses import dataclass
from typing import Any

import pyray as ray
import tomllib

#TJA Format creator is unknown. I did not create the format, but I did write the parser though.

def get_zip_filenames(zip_path: str) -> list[str]:
    result = []
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        for file_name in file_list:
            result.append(file_name)
    return result

def load_image_from_zip(zip_path: str, filename: str) -> ray.Image:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        with zip_ref.open(filename) as image_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(image_file.read())
                temp_file_path = temp_file.name
        image = ray.load_image(temp_file_path)
        os.remove(temp_file_path)
        return image

def load_texture_from_zip(zip_path: str, filename: str) -> ray.Texture:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        with zip_ref.open(filename) as image_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(image_file.read())
                temp_file_path = temp_file.name
        texture = ray.load_texture(temp_file_path)
        os.remove(temp_file_path)
        return texture

def load_all_textures_from_zip(zip_path: str) -> dict[str, list[ray.Texture]]:
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

@dataclass
class GlobalData:
    videos_cleared = False
    start_song: bool = False
    selected_song: str = ''
    selected_difficulty: int = -1
    result_good: int = -1
    result_ok: int = -1
    result_bad: int = -1
    result_score: int = -1
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
