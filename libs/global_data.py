from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Modifiers:
    auto: bool = False
    speed: float = 1.0
    display: bool = False
    inverse: bool = False
    random: int = 0

@dataclass
class GlobalData:
    selected_song: Path = Path()
    songs_played: int = 0
    config: dict = field(default_factory=lambda: dict())
    song_hashes: dict[str, list[dict]] = field(default_factory=lambda: dict()) #Hash to path
    song_paths: dict[Path, str] = field(default_factory=lambda: dict()) #path to hash
    song_progress: float = 0.0
    total_songs: int = 0
    hit_sound: int = 0
    player_num: int = 1
    input_locked: bool = False
    modifiers: Modifiers = field(default_factory=lambda: Modifiers())

global_data = GlobalData()
