from pathlib import Path

import pyray as ray


class TextureWrapper:
    def __init__(self):
        pass
    def load_texture(self, texture: Path) -> ray.Texture:
        return ray.load_texture(str(texture))
