from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, TypedDict

class Difficulty(IntEnum):
    EASY = 0
    NORMAL = 1
    HARD = 2
    ONI = 3
    URA = 4
    TOWER = 5
    DAN = 6

class Crown(IntEnum):
    NONE = 0
    CLEAR = 1
    FC = 2
    DFC = 3

class GeneralConfig(TypedDict):
    fps_counter: bool
    audio_offset: int
    visual_offset: int
    language: str
    hard_judge: int
    touch_enabled: bool
    timer_frozen: bool
    judge_counter: bool
    nijiiro_notes: bool
    log_level: int
    fake_online: bool

class NameplateConfig(TypedDict):
    name: str
    title: str
    title_bg: int
    dan: int
    gold: bool
    rainbow: bool

class PathsConfig(TypedDict):
    tja_path: list[str]
    video_path: list[str]

class KeysConfig(TypedDict):
    exit_key: str
    fullscreen_key: str
    borderless_key: str
    back_key: str
    restart_key: str

class Keys1PConfig(TypedDict):
    left_kat: list[str]
    left_don: list[str]
    right_don: list[str]
    right_kat: list[str]

class Keys2PConfig(TypedDict):
    left_kat: list[str]
    left_don: list[str]
    right_don: list[str]
    right_kat: list[str]

class GamepadConfig(TypedDict):
    left_kat: list[int]
    left_don: list[int]
    right_don: list[int]
    right_kat: list[int]

class AudioConfig(TypedDict):
    device_type: int
    sample_rate: int
    buffer_size: int

class VolumeConfig(TypedDict):
    sound: float
    music: float
    voice: float
    hitsound: float
    attract_mode: float

class VideoConfig(TypedDict):
    screen_width: int
    screen_height: int
    fullscreen: bool
    borderless: bool
    target_fps: int
    vsync: bool

class Config(TypedDict):
    general: GeneralConfig
    nameplate_1p: NameplateConfig
    nameplate_2p: NameplateConfig
    paths: PathsConfig
    keys: KeysConfig
    keys_1p: Keys1PConfig
    keys_2p: Keys2PConfig
    gamepad: GamepadConfig
    audio: AudioConfig
    volume: VolumeConfig
    video: VideoConfig

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
class DanResultSong:
    """
    Data class for storing dan result song data.
    """
    selected_difficulty: int = 0
    diff_level: int = 0
    song_title: str = "default_title"
    genre_index: int = 0
    good: int = 0
    ok: int = 0
    bad: int = 0
    drumroll: int = 0

class DanResultExam:
    """
    Data class for storing dan result exam data.
    """
    progress: float = 0
    counter_value: int = 0
    bar_texture: str = "exam_red"
    failed: bool = False

@dataclass
class DanResultData:
    """
    Data class for storing dan result data.
    """
    dan_color: int = 0
    dan_title: str = "default_title"
    score: int = 0
    gauge_length: float = 0.0
    max_combo: int = 0
    songs: list[DanResultSong] = field(default_factory=list)
    exams: list[Any] = field(default_factory=list)
    exam_data: list[DanResultExam] = field(default_factory=list)

@dataclass
class ResultData:
    """
    Data class for storing result data.
    result_score: The score achieved in the game.
    result_good: The number of good notes achieved in the game.
    result_ok: The number of ok notes achieved in the game.
    result_bad: The number of bad notes achieved in the game.
    result_max_combo: The maximum combo achieved in the game.
    result_total_drumroll: The total drumroll achieved in the game.
    result_gauge_length: The length of the gauge achieved in the game.
    prev_score: The previous score pulled from the database.
    """
    score: int = 0
    good: int = 0
    ok: int = 0
    bad: int = 0
    max_combo: int = 0
    total_drumroll: int = 0
    gauge_length: float = 0
    prev_score: int = 0

@dataclass
class SessionData:
    """Data class for storing session data. Wiped after the result screen.
    selected_song (Path): The currently selected song.
    selected_dan (list[tuple[Any, int, int]]): The currently selected dan songs (TJA). TJAParser, Genre Index, Difficulty
    selected_dan_exam: list[Exam]: list of dan requirements, contains Exam objects
    dan_color: int: The emblem color of the selected dan
    selected_difficulty: The difficulty level selected by the user.
    song_title: The title of the song being played.
    genre_index: The index of the genre being played."""
    selected_song: Path = Path()
    selected_dan: list[tuple[Any, int, int, int]] = field(default_factory=lambda: [])
    selected_dan_exam: list[Any] = field(default_factory=lambda: [])
    dan_color: int = 0
    selected_difficulty: int = 0
    song_title: str = "default_title"
    genre_index: int = 0
    result_data: ResultData = field(default_factory=lambda: ResultData())
    dan_result_data: DanResultData = field(default_factory=lambda: DanResultData())

@dataclass
class GlobalData:
    """
    Global data for the game. Should be accessed via the global_data variable.

    Attributes:
        songs_played (int): The number of songs played.
        config (dict): The configuration settings.
        song_hashes (dict[str, list[dict]]): A dictionary mapping song hashes to their metadata.
        song_paths (dict[Path, str]): A dictionary mapping song paths to their hashes.
        song_progress (float): The progress of the loading bar.
        total_songs (int): The total number of songs.
        hit_sound (list[int]): The indices of the hit sounds currently used.
        player_num (int): The player number. Either 1 or 2.
        input_locked (int): The input lock status. 0 means unlocked, 1 or greater means locked.
        modifiers (list[Modifiers]): The modifiers for the game.
        session_data (list[SessionData]): Session data for both players.
    """
    songs_played: int = 0
    config: Config = field(default_factory=dict)
    song_hashes: dict[str, list[dict]] = field(default_factory=lambda: dict()) #Hash to path
    song_paths: dict[Path, str] = field(default_factory=lambda: dict()) #path to hash
    song_progress: float = 0.0
    total_songs: int = 0
    hit_sound: list[int] = field(default_factory=lambda: [0, 0])
    player_num: int = 1
    input_locked: int = 0
    modifiers: list[Modifiers] = field(default_factory=lambda: [Modifiers(), Modifiers()])
    session_data: list[SessionData] = field(default_factory=lambda: [SessionData(), SessionData()])

global_data = GlobalData()

def reset_session():
    """Reset the session data."""
    global_data.session_data[0] = SessionData()
    global_data.session_data[1] = SessionData()
