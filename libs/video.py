from pathlib import Path
import logging

import pyray as ray
from moviepy import VideoFileClip

from libs.audio import audio
from libs.utils import get_current_ms

logger = logging.getLogger(__name__)

class VideoPlayer:
    def __init__(self, path: Path):
        """Initialize a video player instance"""
        self.is_finished_list = [False, False]
        self.video = VideoFileClip(path)
        if self.video.audio is not None:
            self.video.audio.write_audiofile("cache/temp_audio.wav", logger=None)
            self.audio = audio.load_music_stream(Path("cache/temp_audio.wav"), 'video')

        self.texture = None
        self.current_frame_data = None

        self.frame_timestamps: list[float] = [(i * 1000) / self.video.fps for i in range(int(self.video.duration * self.video.fps) + 1)]

        self.start_ms = None
        self.frame_index = 0
        self.fps = self.video.fps
        self.frame_duration = 1000 / self.fps
        self.audio_played = False

    def _audio_manager(self):
        if self.audio is None:
            return
        if self.is_finished_list[1]:
            return
        if not self.audio_played:
            audio.play_music_stream(self.audio, 'attract_mode')
            self.audio_played = True
        audio.update_music_stream(self.audio)
        self.is_finished_list[1] = audio.get_music_time_length(self.audio) <= audio.get_music_time_played(self.audio)

    def _load_frame(self, index: int):
        """Load a specific frame and update the texture"""
        if index >= len(self.frame_timestamps) or index < 0:
            return False

        try:
            timestamp = self.frame_timestamps[index]
            time_sec = timestamp / 1000
            frame_data = self.video.get_frame(time_sec)

            if self.texture is None:
                image = ray.Image(frame_data, self.video.w, self.video.h, 1, ray.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8)
                self.texture = ray.load_texture_from_image(image)
            else:
                if frame_data is not None:
                    frame_bytes = frame_data.tobytes()
                    pixels_ptr = ray.ffi.cast('void *', ray.ffi.from_buffer('unsigned char[]', frame_bytes))
                    ray.update_texture(self.texture, pixels_ptr)

            self.current_frame_data = frame_data
            return True
        except Exception as e:
            logger.error(f"Error loading frame at index {index}: {e}")
            return False

    def is_started(self) -> bool:
        """Returns boolean value if the video has begun"""
        return self.start_ms is not None

    def start(self, current_ms: float) -> None:
        """Start video playback at call time"""
        self.start_ms = current_ms
        self._load_frame(0)

    def is_finished(self) -> bool:
        """Check if video is finished playing"""
        return all(self.is_finished_list)

    def set_volume(self, volume: float) -> None:
        """Set video volume, takes float value from 0.0 to 1.0"""
        audio.set_music_volume(self.audio, volume)

    def update(self):
        """Updates video playback, advancing frames and audio"""
        self._audio_manager()

        if self.frame_index >= len(self.frame_timestamps):
            self.is_finished_list[0] = True
            return

        if self.start_ms is None:
            return

        elapsed_time = get_current_ms() - self.start_ms

        while (self.frame_index < len(self.frame_timestamps) and
               elapsed_time >= self.frame_timestamps[self.frame_index]):
            self.frame_index += 1

        current_index = max(0, self.frame_index - 1)

        self._load_frame(current_index)

    def draw(self):
        """Draw video frames to the raylib canvas"""
        if self.texture is not None:
            ray.draw_texture(self.texture, 0, 0, ray.WHITE)

    def stop(self):
        """Stops the video, audio, and clears its buffer"""
        self.video.close()

        if self.texture is not None:
            ray.unload_texture(self.texture)
            self.texture = None

        if self.audio is not None:
            if audio.is_music_stream_playing(self.audio):
                audio.stop_music_stream(self.audio)
            audio.unload_music_stream(self.audio)

        if Path("cache/temp_audio.wav").exists():
            Path("cache/temp_audio.wav").unlink()
