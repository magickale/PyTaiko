import moviepy
import pyray as ray

from libs.audio import audio
from libs.utils import get_current_ms


class VideoPlayer:
    def __init__(self, path):
        self.is_finished_list = [False, False]
        self.video_path = path
        self.video = moviepy.VideoFileClip(path)
        audio_path = path[:-4] + '.ogg'
        self.audio = audio.load_music_stream(audio_path)

        self.buffer_size = 10  # Number of frames to keep in memory
        self.frame_buffer = {}  # Dictionary to store frames {timestamp: texture}
        self.frame_timestamps = [(i * 1000) / self.video.fps for i in range(int(self.video.duration * self.video.fps) + 1)]

        self.start_ms = None
        self.frame_index = 0
        self.current_frame = None
        self.fps = self.video.fps
        self.frame_duration = 1000 / self.fps

    def _audio_manager(self):
        if not audio.is_music_stream_playing(self.audio):
            audio.play_music_stream(self.audio)
        audio.update_music_stream(self.audio)
        time_played = audio.get_music_time_played(self.audio) / audio.get_music_time_length(self.audio)
        ending_lenience = 0.95
        if time_played > ending_lenience:
            self.is_finished_list[1] = True

    def _load_frame(self, index):
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

    def is_started(self):
        return self.start_ms is not None

    def start(self, current_ms):
        self.start_ms = current_ms
        for i in range(min(self.buffer_size, len(self.frame_timestamps))):
            self._load_frame(i)

    def is_finished(self):
        return all(self.is_finished_list)

    def set_volume(self, volume):
        audio.set_music_volume(self.audio, volume)
    def update(self):
        self._audio_manager()

        if self.frame_index >= len(self.frame_timestamps) - 1:
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
        if self.current_frame is not None:
            ray.draw_texture(self.current_frame, 0, 0, ray.WHITE)

    def stop(self):
        for timestamp, texture in self.frame_buffer.items():
            ray.unload_texture(texture)
        self.frame_buffer.clear()

        if audio.is_music_stream_playing(self.audio):
            audio.stop_music_stream(self.audio)
