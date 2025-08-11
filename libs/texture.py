import copy
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Union

import pyray as ray

from libs.animation import BaseAnimation, parse_animations


class Texture:
    def __init__(self, name: str, texture: Union[ray.Texture, list[ray.Texture]], init_vals: dict[str, int]):
        self.name = name
        self.texture = texture
        self.init_vals = init_vals
        if isinstance(self.texture, list):
            self.width = self.texture[0].width
            self.height = self.texture[0].height
        else:
            self.width = self.texture.width
            self.height = self.texture.height
        self.is_frames = isinstance(self.texture, list)

        self.x = 0
        self.y = 0
        self.x2 = self.width
        self.y2 = self.height

class TextureWrapper:
    def __init__(self):
        self.textures: dict[str, dict[str, Texture]] = dict()
        self.animations: dict[int, BaseAnimation] = dict()
        self.graphics_path = Path("Graphics")

    def unload_textures(self):
        for zip in self.textures:
            for file in self.textures[zip]:
                tex_object = self.textures[zip][file]
                if isinstance(tex_object.texture, list):
                    for texture in tex_object.texture:
                        ray.unload_texture(texture)
                else:
                    ray.unload_texture(tex_object.texture)

    def get_animation(self, index: int, is_copy: bool = False):
        if index not in self.animations:
            raise Exception(f"Unable to find id {index} in loaded animations")
        if is_copy:
            return copy.deepcopy(self.animations[index])
        return self.animations[index]

    def update_attr(self, subset: str, texture: str, attr: str, value: float | int):
        tex_object = self.textures[subset][texture]
        if hasattr(tex_object, attr):
            setattr(tex_object, attr, tex_object.init_vals[attr] + value)

    def _read_tex_obj_data(self, tex_mapping: dict, tex_object: Texture):
        tex_object.x = tex_mapping.get("x", 0)
        tex_object.y = tex_mapping.get("y", 0)
        tex_object.x2 = tex_mapping.get("x2", tex_object.width)
        tex_object.y2 = tex_mapping.get("y2", tex_object.height)

    def load_screen_textures(self, screen_name: str) -> None:
        self.unload_textures()
        screen_path = self.graphics_path / screen_name
        if (screen_path / 'animation.json').exists():
            with open(screen_path / 'animation.json') as json_file:
                self.animations = parse_animations(json.loads(json_file.read()))
        for zip in screen_path.iterdir():
            if zip.is_dir() or zip.suffix != ".zip":
                continue
            with zipfile.ZipFile(zip, 'r') as zip_ref:
                if 'texture.json' not in zip_ref.namelist():
                    raise Exception(f"texture.json file missing from {zip}")

                with zip_ref.open('texture.json') as json_file:
                    tex_mapping_data = json.loads(json_file.read().decode('utf-8'))
                    self.textures[zip.stem] = dict()

                for tex_name in tex_mapping_data:
                    if f"{tex_name}/" in zip_ref.namelist():
                        tex_mapping = tex_mapping_data[tex_name]

                        with tempfile.TemporaryDirectory() as temp_dir:
                            zip_ref.extractall(temp_dir, members=[name for name in zip_ref.namelist()
                                                                if name.startswith(tex_name)])

                            extracted_path = Path(temp_dir) / tex_name
                            if extracted_path.is_dir():
                                frames = [ray.load_texture(str(frame)) for frame in sorted(extracted_path.iterdir(),
                                          key=lambda x: int(x.stem)) if frame.is_file()]
                            else:
                                frames = [ray.load_texture(str(extracted_path))]
                        self.textures[zip.stem][tex_name] = Texture(tex_name, frames, tex_mapping)
                        self._read_tex_obj_data(tex_mapping, self.textures[zip.stem][tex_name])
                    elif f"{tex_name}.png" in zip_ref.namelist():
                        tex_mapping = tex_mapping_data[tex_name]

                        png_filename = f"{tex_name}.png"
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                            temp_file.write(zip_ref.read(png_filename))
                            temp_path = temp_file.name

                        try:
                            tex = ray.load_texture(temp_path)
                            self.textures[zip.stem][tex_name] = Texture(tex_name, tex, tex_mapping)
                            self._read_tex_obj_data(tex_mapping, self.textures[zip.stem][tex_name])
                        finally:
                            os.unlink(temp_path)
                    else:
                        raise Exception(f"Texture {tex_name} was not found in {zip}")


    def draw_texture(self, subset: str, texture: str, color: ray.Color=ray.WHITE, frame: int = 0, scale: float = 1.0, center: bool = False, mirror: str = '', x: float = 0, y: float = 0, x2: float = 0, y2: float = 0, origin: ray.Vector2 = ray.Vector2(0,0), rotation: float = 0) -> None:
        mirror_x = -1 if mirror == 'horizontal' else 1
        mirror_y = -1 if mirror == 'vertical' else 1
        tex_object = self.textures[subset][texture]
        source_rect = ray.Rectangle(0, 0, tex_object.width * mirror_x, tex_object.height * mirror_y)
        if center:
            dest_rect = ray.Rectangle(tex_object.x + (tex_object.width//2) - ((tex_object.width * scale)//2) + x, tex_object.y + (tex_object.height//2) - ((tex_object.height * scale)//2) + y, tex_object.x2*scale + x2, tex_object.y2*scale + y2)
        else:
            dest_rect = ray.Rectangle(tex_object.x + x, tex_object.y + y, tex_object.x2*scale + x2, tex_object.y2*scale + y2)
        if tex_object.is_frames:
            if not isinstance(tex_object.texture, list):
                raise Exception("Texture was marked as multiframe but is only 1 texture")
            if frame >= len(tex_object.texture):
                raise Exception(f"Frame {frame} not available in iterable texture {tex_object.name}")
            ray.draw_texture_pro(tex_object.texture[frame], source_rect, dest_rect, origin, rotation, color)
        else:
            if isinstance(tex_object.texture, list):
                raise Exception("Texture is multiframe but was called as 1 texture")
            ray.draw_texture_pro(tex_object.texture, source_rect, dest_rect, origin, rotation, color)

tex = TextureWrapper()
