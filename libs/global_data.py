from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class Modifiers:
    """
    Modifiers for the game.
    """
    auto: bool = False
    speed: float = 1.0
    display: bool = False
    inverse: bool = False
    random: int = 0

@dataclass
class GlobalData:
    """
    Global data for the game. Should be accessed via the global_data variable.

    Attributes:
        selected_song (Path): The currently selected song.
        songs_played (int): The number of songs played.
        config (dict): The configuration settings.
        song_hashes (dict[str, list[dict]]): A dictionary mapping song hashes to their metadata.
        song_paths (dict[Path, str]): A dictionary mapping song paths to their hashes.
        song_progress (float): The progress of the loading bar.
        total_songs (int): The total number of songs.
        hit_sound (int): The index of the hit sound currently used.
        player_num (int): The player number. Either 1 or 2.
        input_locked (int): The input lock status. 0 means unlocked, 1 or greater means locked.
        modifiers (Modifiers): The modifiers for the game.
    """
    selected_song: Path = Path()
    songs_played: int = 0
    config: dict[str, Any] = field(default_factory=lambda: dict())
    song_hashes: dict[str, list[dict]] = field(default_factory=lambda: dict()) #Hash to path
    song_paths: dict[Path, str] = field(default_factory=lambda: dict()) #path to hash
    song_progress: float = 0.0
    total_songs: int = 0
    hit_sound: int = 0
    player_num: int = 1
    input_locked: int = 0
    modifiers: Modifiers = field(default_factory=lambda: Modifiers())

global_data = GlobalData()
