import cv2
import pyray as ray

from libs.audio import audio
from libs.utils import get_current_ms


class VideoPlayer:
    def __init__(self, path: str):
        self.video_path = path
        self.start_ms = None
        self.current_frame = None
        self.last_frame = self.current_frame
        self.frame_index = 0
        self.frames = []
        self.cap = cv2.VideoCapture(self.video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.is_finished_list = [False, False, False]  # Added third flag for frame conversion
        self.all_frames_converted = False
        audio_path = path[:-4] + '.ogg'
        self.audio = audio.load_music_stream(audio_path)

    def is_finished(self) -> bool:
        return all(self.is_finished_list)

    def _convert_frames(self):
        """Legacy method that converts all frames at once"""
        if not self.cap.isOpened():
            raise ValueError("Error: Could not open video file.")

        frame_count = 0
        success, frame = self.cap.read()
        while success:
            timestamp = (frame_count / self.fps * 1000)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            new_frame = ray.Image(frame_rgb.tobytes(), frame_rgb.shape[1], frame_rgb.shape[0], 1, ray.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8)
            self.frames.append((timestamp, new_frame))
            success, frame = self.cap.read()
            frame_count += 1

        self.cap.release()
        print(f"Extracted {len(self.frames)} frames.")
        self.start_ms = get_current_ms()
        self.all_frames_converted = True
        self.is_finished_list[2] = True

    def convert_frames_background(self):
        """Converts a single frame each time it's called"""
        if self.all_frames_converted:
            return

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                raise ValueError("Error: Could not open video file.")

        # Process one frame
        success, frame = self.cap.read()
        if success:
            timestamp = (len(self.frames) / self.fps * 1000)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            new_frame = ray.Image(frame_rgb.tobytes(), frame_rgb.shape[1], frame_rgb.shape[0], 1, ray.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8)
            self.frames.append((timestamp, new_frame))
        else:
            # No more frames to convert
            self.cap.release()
            print(f"Extracted {len(self.frames)} frames.")
            self.all_frames_converted = True
            self.is_finished_list[2] = True

    def _check_for_start(self):
        # Start audio once we have at least one frame
        if len(self.frames) > 0 and not audio.is_music_stream_playing(self.audio):
            audio.play_music_stream(self.audio)

    def _audio_manager(self):
        audio.update_music_stream(self.audio)
        time_played = audio.get_music_time_played(self.audio) / audio.get_music_time_length(self.audio)
        ending_lenience = 0.95
        if time_played > ending_lenience:
            self.is_finished_list[1] = True

    def update(self):
        self._check_for_start()
        self._audio_manager()

        # Check if we've reached the end of available frames
        if self.frame_index == len(self.frames) - 1 and self.all_frames_converted:
            self.is_finished_list[0] = True
            return

        if self.start_ms is None:
            return

        # Only proceed if we have frames to display
        if self.frame_index < len(self.frames):
            timestamp, frame = self.frames[self.frame_index][0], self.frames[self.frame_index][1]
            elapsed_time = get_current_ms() - self.start_ms

            if elapsed_time >= timestamp:
                self.current_frame = ray.load_texture_from_image(frame)
                if self.last_frame != self.current_frame and self.last_frame is not None:
                    ray.unload_texture(self.last_frame)
                self.frame_index += 1
                self.last_frame = self.current_frame

    def draw(self):
        if self.current_frame is not None:
            ray.draw_texture(self.current_frame, 0, 0, ray.WHITE)

    def stop(self):
        if hasattr(self, 'current_frame') and self.current_frame:
            ray.unload_texture(self.current_frame)
        if hasattr(self, 'last_frame') and self.last_frame:
            ray.unload_texture(self.last_frame)
        if audio.is_music_stream_playing(self.audio):
            audio.stop_music_stream(self.audio)
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
