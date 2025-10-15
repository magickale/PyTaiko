from pathlib import Path

import pyray as ray
from moviepy import VideoFileClip

from libs.audio import audio
from libs.utils import get_current_ms


class VideoPlayer:
    def __init__(self, path: Path):
        """Initialize a video player instance"""
        self.is_finished_list = [False, False]
        self.video = VideoFileClip(path)
        if self.video.audio is not None:
            self.video.audio.write_audiofile("cache/temp_audio.wav")
            self.audio = audio.load_music_stream(Path("cache/temp_audio.wav"), 'video')

        self.buffer_size = 10  # Number of frames to keep in memory
        self.frame_buffer: dict[float, ray.Texture] = dict()  # Dictionary to store frames {timestamp: texture}
        self.frame_timestamps: list[float] = [(i * 1000) / self.video.fps for i in range(int(self.video.duration * self.video.fps) + 1)]

        self.start_ms = None
        self.frame_index = 0
        self.current_frame = None
        self.fps = self.video.fps
        self.frame_duration = 1000 / self.fps
        self.audio_played = False

    def _audio_manager(self):
        if self.audio is None:
            return
        if self.is_finished_list[1]:
            return
        if not self.audio_played:
            audio.play_music_stream(self.audio)
            self.audio_played = True
        audio.update_music_stream(self.audio)
        self.is_finished_list[1] = audio.get_music_time_length(self.audio) <= audio.get_music_time_played(self.audio)

    def _load_frame(self, index: int):
        """Load a specific frame into the buffer"""
        if index >= len(self.frame_timestamps) or index < 0:
            return None

        timestamp = self.frame_timestamps[index]

        if timestamp in self.frame_buffer:
            return self.frame_buffer[timestamp]

        try:
            time_sec = timestamp / 1000
            frame_data = self.video.get_frame(time_sec)

            image = ray.Image(frame_data, self.video.w, self.video.h, 1, ray.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8)
            texture = ray.load_texture_from_image(image)

            self.frame_buffer[timestamp] = texture

            self._manage_buffer()

            return texture
        except Exception as e:
            print(f"Error loading frame at index {index}: {e}")
            return None

    def _manage_buffer(self):
        if len(self.frame_buffer) > self.buffer_size:
            keep_range = set()
            half_buffer = self.buffer_size // 2

            for i in range(max(0, self.frame_index - half_buffer),
                          min(len(self.frame_timestamps), self.frame_index + half_buffer + 1)):
                keep_range.add(self.frame_timestamps[i])

            buffer_timestamps = list(self.frame_buffer.keys())
            buffer_timestamps.sort()

            for ts in buffer_timestamps:
                if ts not in keep_range and len(self.frame_buffer) > self.buffer_size:
                    texture = self.frame_buffer.pop(ts)
                    ray.unload_texture(texture)

    def is_started(self) -> bool:
        """Returns boolean value if the video has begun"""
        return self.start_ms is not None

    def start(self, current_ms: float) -> None:
        """Start video playback at call time"""
        self.start_ms = current_ms
        for i in range(min(self.buffer_size, len(self.frame_timestamps))):
            self._load_frame(i)

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

        self.current_frame = self._load_frame(current_index)

        for i in range(1, 5):
            if current_index + i < len(self.frame_timestamps):
                self._load_frame(current_index + i)

    def draw(self):
        """Draw video frames to the raylib canvas"""
        if self.current_frame is not None:
            ray.draw_texture(self.current_frame, 0, 0, ray.WHITE)

    def stop(self):
        """Stops the video, audio, and clears its buffer"""
        self.video.close()
        for timestamp, texture in self.frame_buffer.items():
            ray.unload_texture(texture)
        self.frame_buffer.clear()

        if audio.is_music_stream_playing(self.audio):
            audio.stop_music_stream(self.audio)
        audio.unload_music_stream(self.audio)
        Path("cache/temp_audio.wav").unlink()
