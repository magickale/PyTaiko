import os
import tempfile
import time
import zipfile
from dataclasses import dataclass
from typing import Any

import pyray as ray
import tomllib

#TJA Format creator is unknown. I did not create the format, but I did write the parser though.

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

def rounded(num: float) -> int:
    sign = 1 if (num >= 0) else -1
    num = abs(num)
    result = int(num)
    if (num - result >= 0.5):
        result += 1
    return sign * result

def get_current_ms() -> int:
    return rounded(time.time() * 1000)

def strip_comments(code: str):
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

def get_pixels_per_frame(bpm: float, time_signature: float, distance: float):
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
    start_song: bool = False
    selected_song: str = ''
    selected_difficulty: int = -1
    result_good: int = -1
    result_ok: int = -1
    result_bad: int = -1
    result_score: int = -1
