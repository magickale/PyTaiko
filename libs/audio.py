import os
import queue
import time
from pathlib import Path
from threading import Lock, Thread
from typing import Optional

import soundfile as sf
from numpy import (
    arange,
    clip,
    column_stack,
    float32,
    frombuffer,
    int16,
    int32,
    interp,
    mean,
    multiply,
    ndarray,
    sqrt,
    uint8,
    zeros,
)

os.environ["SD_ENABLE_ASIO"] = "1"
import sounddevice as sd

from libs.utils import get_config, rounded


def resample(data, orig_sr, target_sr):
    # Return original data if no resampling needed
    ratio = target_sr / orig_sr
    if ratio == 1.0:
        return data

    # Handle both mono and multi-channel audio
    if len(data.shape) == 1:  # Mono audio
        return _resample_channel(data, orig_sr, target_sr)
    else:  # Multi-channel audio
        num_channels = data.shape[1]
        resampled_channels = []

        for ch in range(num_channels):
            channel_data = data[:, ch]
            resampled_channel = _resample_channel(channel_data, orig_sr, target_sr)
            resampled_channels.append(resampled_channel)

        return column_stack(resampled_channels)

def _resample_channel(channel_data, orig_sr, target_sr):
    # Calculate number of samples in resampled audio
    orig_length = len(channel_data)
    new_length = int(orig_length * target_sr / orig_sr)

    # Create time points for original and new sample rates
    orig_time = arange(orig_length) / orig_sr
    new_time = arange(new_length) / target_sr

    # Perform linear interpolation
    resampled_data = interp(new_time, orig_time, channel_data)

    return resampled_data

def get_np_array(sample_width, raw_data):
    if sample_width == 1:
        # 8-bit samples are unsigned
        data = frombuffer(raw_data, dtype=uint8)
        return (data.astype(float32) - 128) / 128.0
    elif sample_width == 2:
        # 16-bit samples are signed
        data = frombuffer(raw_data, dtype=int16)
        return data.astype(float32) / 32768.0
    elif sample_width == 3:
        # 24-bit samples handling
        data = zeros(len(raw_data) // 3, dtype=int32)
        for i in range(len(data)):
            data[i] = int.from_bytes(raw_data[i*3:i*3+3], byteorder='little', signed=True)
        return data.astype(float32) / (2**23)
    elif sample_width == 4:
        # 32-bit samples are signed
        data = frombuffer(raw_data, dtype=int32)
        return data.astype(float32) / (2**31)
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

def get_average_volume_rms(data):
    """Calculate average volume using RMS method"""
    rms = sqrt(mean(data ** 2))
    return rms

class Sound:
    def __init__(self, file_path: Path, data: Optional[ndarray]=None, target_sample_rate: int=44100):
        self.file_path = file_path
        self.data = data
        self.channels = 0
        self.sample_rate = target_sample_rate
        self.position = 0
        self.is_playing = False
        self.is_paused = False
        self.volume = 1.0
        self.pan = 0.5  # 0.0 = left, 0.5 = center, 1.0 = right
        self.normalize: Optional[float] = None

        if file_path.exists():
            self.load()

    def load(self) -> None:
        """Load and prepare the sound file data"""
        data, original_sample_rate = sf.read(str(self.file_path))

        if data.ndim == 1:
            self.channels = 1
            data = data.reshape(-1, 1)
        else:
            self.channels = data.shape[1]

        if original_sample_rate != self.sample_rate:
            print(f"Resampling {self.file_path} from {original_sample_rate}Hz to {self.sample_rate}Hz")
            data = resample(data, original_sample_rate, self.sample_rate)

        if self.normalize is not None:
            current_rms = get_average_volume_rms(data)
            if current_rms > 0:  # Avoid division by zero
                target_rms = self.normalize
                rms_scale_factor = target_rms / current_rms
                data *= rms_scale_factor

        self.data = data

    def play(self) -> None:
        self.position = 0
        self.is_playing = True
        self.is_paused = False

    def stop(self) -> None:
        self.is_playing = False
        self.is_paused = False
        self.position = 0

    def pause(self) -> None:
        if self.is_playing:
            self.is_paused = True
            self.is_playing = False

    def resume(self) -> None:
        if self.is_paused:
            self.is_playing = True
            self.is_paused = False

    def normalize_vol(self, rms: float) -> None:
        self.normalize = rms
        if self.data is not None:
            self.data = None
        self.load()

    def get_frames(self, num_frames: int) -> Optional[ndarray]:
        """Get the next num_frames of audio data, applying volume, pitch, and pan"""
        if self.data is None:
            return
        if not self.is_playing:
            # Return silence if not playing
            if self.channels == 1:
                return zeros(num_frames, dtype=float32)
            else:
                return zeros((num_frames, self.channels), dtype=float32)

        # Calculate how many frames we have left
        frames_left = len(self.data) - self.position
        if self.channels > 1:
            frames_left = self.data.shape[0] - self.position

        if frames_left <= 0:
            # We've reached the end of the sound
            self.is_playing = False
            if self.channels == 1:
                return zeros(num_frames, dtype=float32)
            else:
                return zeros((num_frames, self.channels), dtype=float32)

        # Get the actual frames to return
        frames_to_get = min(num_frames, frames_left)

        if self.channels == 1:
            output = zeros(num_frames, dtype=float32)
            output[:frames_to_get] = self.data[self.position:self.position+frames_to_get].flatten()
        else:
            output = zeros((num_frames, self.channels), dtype=float32)
            output[:frames_to_get] = self.data[self.position:self.position+frames_to_get]

        self.position += frames_to_get

        output *= self.volume

        # Apply pan for stereo output
        if self.channels == 2 and self.pan != 0.5:
            # pan=0: full left, pan=0.5: center, pan=1: full right
            left_vol = min(1.0, 2.0 * (1.0 - self.pan))
            right_vol = min(1.0, 2.0 * self.pan)
            output[:, 0] *= left_vol
            output[:, 1] *= right_vol
        return output

class Music:
    def __init__(self, file_path: Path, data: Optional[ndarray]=None, target_sample_rate: int=44100, sample_rate: int =44100, preview: Optional[float]=None, normalize: Optional[float]=None):
        self.file_path = file_path
        self.data = data
        self.target_sample_rate = target_sample_rate
        self.sample_rate = sample_rate
        self.channels = 0
        self.position = 0  # In frames (original sample rate)
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.75
        self.pan = 0.5  # Center
        self.total_frames = 0
        self.valid = False
        self.normalize = normalize
        self.preview = preview  # Preview start time in seconds
        self.is_preview_mode = preview is not None

        # Add preview-specific attributes
        self.preview_start_frame = 0
        self.preview_end_frame = 0
        self.uses_file_streaming = False  # Flag to indicate streaming vs memory loading

        self.file_buffer_size = int(target_sample_rate * 5)  # 5 seconds buffer
        self.buffer = None
        self.buffer_position = 0
        self.buffer_original_frames = 0  # Track original frames for resampling

        # Thread-safe updates
        self.lock = Lock()
        self.sound_file = None

        if self.file_path.exists():
            self.load_from_file()
        else:
            self.load_from_memory()

    def load_from_memory(self) -> None:
        """Load music from in-memory numpy array"""
        try:
            if self.data is None:
                raise Exception("No data provided for memory loading")

            # Convert to float32 if needed
            if self.data.dtype != float32:
                self.data = self.data.astype(float32)

            if self.sample_rate != self.target_sample_rate:
                print(f"Resampling {self.file_path} from {self.sample_rate}Hz to {self.target_sample_rate}Hz")
                self.data = resample(self.data, self.sample_rate, self.target_sample_rate)

            if self.normalize is not None:
                current_rms = get_average_volume_rms(self.data)
                if current_rms > 0:  # Avoid division by zero
                    target_rms = self.normalize
                    rms_scale_factor = target_rms / current_rms
                    self.data *= rms_scale_factor

            # Determine channels and total frames
            if self.data.ndim == 1:
                self.channels = 1
                self.total_frames = len(self.data)
                # Reshape for consistency
                self.data = self.data.reshape(-1, 1)
            else:
                self.channels = self.data.shape[1]
                self.total_frames = self.data.shape[0]

            self.sample_width = 4  # float32
            self.uses_file_streaming = False
            self._fill_buffer()
            self.valid = True
            print(f"Music loaded from memory: {self.channels} channels, {self.sample_rate}Hz, {self.total_frames} frames")

        except Exception as e:
            print(f"Error loading music from memory: {e}")
            self.valid = False

    def load_from_file(self) -> None:
        """Load music from file"""
        try:
            self.sound_file = sf.SoundFile(str(self.file_path))

            # Get file properties
            self.channels = self.sound_file.channels
            self.sample_width = 2 if self.sound_file.subtype in ['PCM_16', 'VORBIS'] else 4
            self.sample_rate = self.sound_file.samplerate
            original_total_frames = self.sound_file.frames

            if self.is_preview_mode:
                # Calculate preview boundaries but don't load data into memory
                self.preview_start_frame = int(self.preview * self.sample_rate)

                # For preview, we'll calculate the available frames from the start position
                available_frames = original_total_frames - self.preview_start_frame
                self.preview_end_frame = min(self.preview_start_frame + available_frames, original_total_frames)

                # Ensure preview start is within bounds
                if self.preview_start_frame >= original_total_frames:
                    self.preview_start_frame = max(0, original_total_frames - available_frames)
                    self.preview_end_frame = original_total_frames

                # Set total frames to the preview length
                self.total_frames = self.preview_end_frame - self.preview_start_frame

                # Seek to preview start position
                self.sound_file.seek(self.preview_start_frame)

                # Enable file streaming mode (don't load into memory)
                self.uses_file_streaming = True
                self.data = None  # Don't store full data in memory

                print(f"Preview mode: Streaming {self.total_frames} frames ({self.total_frames/self.sample_rate:.2f}s) starting at {self.preview:.2f}s")

            else:
                # For non-preview mode, load entire file into memory as before
                self.data = self.sound_file.read()
                self.total_frames = original_total_frames
                self.uses_file_streaming = False

                # Process the loaded data
                self.load_from_memory()
                return  # Early return to avoid duplicate processing

            # Initialize buffer for streaming mode
            self._fill_buffer()
            self.valid = True

            if self.is_preview_mode:
                print(f"Music preview streaming: {self.channels} channels, {self.sample_rate}Hz, {self.total_frames} frames ({self.get_time_length():.2f}s)")
            else:
                print(f"Music loaded: {self.channels} channels, {self.sample_rate}Hz, {self.total_frames} frames")

        except Exception as e:
            print(f"Error loading music file: {e}")
            if hasattr(self, 'sound_file') and self.sound_file:
                self.sound_file.close()
                self.sound_file = None
            self.valid = False

    def _fill_buffer(self) -> bool:
        """Fill buffer from either memory or file stream"""
        try:
            if self.uses_file_streaming:
                return self._fill_buffer_from_file()
            else:
                return self._fill_buffer_from_memory()
        except Exception as e:
            print(f"Error filling buffer: {e}")
            return False

    def _fill_buffer_from_memory(self) -> bool:
        """Fill buffer from in-memory data"""
        if self.data is None:
            return False

        start_frame = self.position
        end_frame = min(start_frame + self.file_buffer_size, self.total_frames)

        if start_frame >= self.total_frames:
            return False

        # Extract the chunk of data
        data_chunk = self.data[start_frame:end_frame]

        self.buffer = data_chunk
        self.buffer_position = 0
        # For memory mode, original frames equals buffer frames since no resampling happens here
        self.buffer_original_frames = len(data_chunk) if data_chunk.ndim == 1 else data_chunk.shape[0]
        return True

    def _fill_buffer_from_file(self) -> bool:
        """Fill buffer by streaming from file"""
        if not self.sound_file:
            return False

        # Calculate current absolute position in file (in original sample rate)
        current_absolute_position = self.preview_start_frame + self.position

        # Check if we've reached the end of the preview
        if current_absolute_position >= self.preview_end_frame:
            return False

        # Calculate how many frames to read (respecting preview boundaries)
        # This is in the original sample rate
        frames_to_read = min(self.file_buffer_size, self.preview_end_frame - current_absolute_position)

        if frames_to_read <= 0:
            return False

        # Seek to the correct position
        self.sound_file.seek(current_absolute_position)

        # Read the data chunk
        data_chunk = self.sound_file.read(frames_to_read)

        if len(data_chunk) == 0:
            return False

        # Store the original length before any processing
        original_frames = len(data_chunk) if data_chunk.ndim == 1 else data_chunk.shape[0]

        # Apply resampling if needed
        if self.sample_rate != self.target_sample_rate:
            data_chunk = resample(data_chunk, self.sample_rate, self.target_sample_rate)

        # Apply normalization if needed
        if self.normalize is not None:
            current_rms = get_average_volume_rms(data_chunk)
            if current_rms > 0:
                target_rms = self.normalize
                rms_scale_factor = target_rms / current_rms
                data_chunk *= rms_scale_factor

        # Ensure proper shape
        if data_chunk.ndim == 1 and self.channels > 1:
            data_chunk = data_chunk.reshape(-1, self.channels)
        elif data_chunk.ndim == 2 and self.channels == 1:
            data_chunk = data_chunk.flatten().reshape(-1, 1)

        self.buffer = data_chunk
        self.buffer_position = 0

        # Store how many original frames this buffer represents
        # This is crucial for position tracking when resampling occurs
        self.buffer_original_frames = original_frames

        return True

    def update(self) -> None:
        """Update music stream buffers"""
        if not self.is_playing or self.is_paused:
            return

        with self.lock:
            # Check if we need to refill the buffer
            if self.buffer is None:
                return
            if self.buffer_position >= len(self.buffer):
                # Update position based on original frames consumed
                if self.uses_file_streaming:
                    # For file streaming, we need to track position in original sample rate
                    self.position += self.buffer_original_frames
                else:
                    # For memory mode, position is already in target sample rate
                    self.position += self.buffer_position
                self.buffer_position = 0
                self.is_playing = self._fill_buffer()

    def play(self) -> None:
        """Start playing the music stream"""
        with self.lock:
            # Reset position if at the end
            if self.position >= self.total_frames:
                self.position = 0
                self.buffer_position = 0
                if self.sound_file and self.uses_file_streaming:
                    self.sound_file.seek(self.preview_start_frame)
                    self._fill_buffer()

            self.is_playing = True
            self.is_paused = False

    def stop(self) -> None:
        """Stop playing the music stream"""
        with self.lock:
            self.is_playing = False
            self.is_paused = False
            self.position = 0
            self.buffer_position = 0
            if self.sound_file and self.uses_file_streaming:
                self.sound_file.seek(self.preview_start_frame)
                self._fill_buffer()

    def pause(self) -> None:
        """Pause the music playback"""
        with self.lock:
            if self.is_playing:
                self.is_paused = True
                self.is_playing = False

    def resume(self) -> None:
        """Resume the music playback"""
        with self.lock:
            if self.is_paused:
                self.is_playing = True
                self.is_paused = False

    def seek(self, position_seconds) -> None:
        """Seek to a specific position in seconds (relative to preview start if in preview mode)"""
        with self.lock:
            # Convert seconds to frames
            frame_position = int(position_seconds * self.target_sample_rate)

            # Clamp position to valid range
            frame_position = max(0, min(frame_position, self.total_frames - 1))

            self.position = frame_position
            self.buffer_position = 0

            # For file streaming, we'll let _fill_buffer handle the seeking
            self._fill_buffer()

    def get_time_length(self) -> float:
        """Get the total length of the music in seconds (preview length if in preview mode)"""
        return self.total_frames / self.target_sample_rate

    def get_time_played(self) -> float:
        """Get the current playback position in seconds (relative to preview start if in preview mode)"""
        return (self.position + self.buffer_position) / self.target_sample_rate

    def get_actual_time_played(self) -> float:
        """Get the actual playback position in the original file (including preview offset)"""
        base_time = (self.position + self.buffer_position) / self.target_sample_rate
        if self.is_preview_mode and self.preview is not None:
            return base_time + self.preview
        return base_time

    def get_frames(self, num_frames) -> ndarray:
        """Get the next num_frames of music data, applying volume, pitch, and pan"""
        if not self.is_playing:
            # Return silence if not playing
            if self.channels == 1:
                return zeros(num_frames, dtype=float32)
            else:
                return zeros((num_frames, self.channels), dtype=float32)

        with self.lock:
            if self.buffer is None:
                return zeros(num_frames, dtype=float32)

            # Check if we need more data
            if self.buffer_position >= len(self.buffer):
                # Update position based on what we actually consumed from the original file
                if self.uses_file_streaming:
                    # For file streaming, advance by original frames (before resampling)
                    self.position += self.buffer_original_frames
                else:
                    # For memory mode, advance by resampled frames
                    self.position += self.buffer_position
                self.buffer_position = 0

                # Try to fill buffer again
                if not self._fill_buffer():
                    self.is_playing = False
                    if self.channels == 1:
                        return zeros(num_frames, dtype=float32)
                    else:
                        return zeros((num_frames, self.channels), dtype=float32)

            # Calculate how many frames we have left in buffer
            frames_left_in_buffer = len(self.buffer) - self.buffer_position
            if self.channels > 1:
                frames_left_in_buffer = self.buffer.shape[0] - self.buffer_position

            frames_to_get = min(num_frames, frames_left_in_buffer)

            if self.channels == 1:
                output = zeros(num_frames, dtype=float32)
                output[:frames_to_get] = self.buffer[self.buffer_position:self.buffer_position+frames_to_get].flatten()
            else:
                output = zeros((num_frames, self.channels), dtype=float32)
                output[:frames_to_get] = self.buffer[self.buffer_position:self.buffer_position+frames_to_get]

            # Update buffer position
            self.buffer_position += frames_to_get

            # Apply volume
            output *= self.volume

            # Apply pan for stereo output
            if self.channels == 2 and self.pan != 0.5:
                # pan=0: full left, pan=0.5: center, pan=1: full right
                left_vol = min(1.0, 2.0 * (1.0 - self.pan))
                right_vol = min(1.0, 2.0 * self.pan)

                output[:, 0] *= left_vol
                output[:, 1] *= right_vol

            return output

    def __del__(self) -> None:
        """Cleanup when the music object is deleted"""
        if hasattr(self, 'sound_file') and self.sound_file:
            try:
                self.sound_file.close()
            except Exception:
                raise Exception("unable to close music stream")

class AudioEngine:
    def __init__(self, type: str) -> None:
        self.target_sample_rate = 44100
        self.buffer_size = 10
        self.sounds: dict[str, Sound] = {}
        self.music_streams = {}
        self.stream = None
        self.device_id = None
        self.running = False
        self.sound_queue: queue.Queue[str] = queue.Queue()
        self.music_queue = queue.Queue()
        self.master_volume = 0.70
        self.output_channels = 2  # Default to stereo
        self.audio_device_ready = False

        # Threading for music stream updates
        self.update_thread = None
        self.update_thread_running = False
        self.type = type

        self._output_buffer = None
        self._channel_conversion_buffer = None
        self._expected_frames = None

    def _initialize_api(self) -> bool:
        """Set up API device"""
        # Find API and use its default device
        hostapis = sd.query_hostapis()
        api_index = -1
        for i, api in enumerate(hostapis):
            if isinstance(api, dict) and 'name' in api and api['name'] == self.type:
                api_index = i
                break

        if isinstance(hostapis, tuple):
            api = hostapis[api_index]
            if isinstance(api, dict) and 'default_output_device' in api:
                default_asio_device = api['default_output_device']
            else:
                raise Exception("Warning: 'default_output_device' key not found in ASIO API info.")
            if default_asio_device >= 0:
                self.device_id = default_asio_device
                device_info = sd.query_devices(self.device_id)
                if isinstance(device_info, sd.DeviceList):
                    raise Exception("Invalid ASIO Device")
                print(f"Using default ASIO device: {device_info['name']}")
                self.buffer_size = rounded(device_info['default_low_output_latency']*1000)
                if 'buffer_size' in get_config()['audio']:
                    self.buffer_size = get_config()['audio']['buffer_size']
                self.target_sample_rate = device_info['default_samplerate']
                if 'sample_rate' in get_config()['audio']:
                    self.target_sample_rate = get_config()['audio']['sample_rate']
                    if self.target_sample_rate == -1:
                        self.target_sample_rate = device_info['default_samplerate']
                # Set output channels based on device capabilities
                self.output_channels = device_info['max_output_channels']
                if self.output_channels > 2:
                    # Limit to stereo for simplicity
                    self.output_channels = 2
                return True
            else:
                print("ASIO API not found, using system default device.")

        # If we get here, use default system device
        self.device_id = None
        device_info = sd.query_devices(sd.default.device[1])
        if isinstance(device_info, sd.DeviceList):
            raise Exception("Invalid ASIO Device")
        self.output_channels = min(2, device_info['max_output_channels'])
        return True

    def _audio_callback(self, outdata: ndarray, frames: int, time: int, status: str) -> None:
        """callback function for the sounddevice stream"""

        if self._output_buffer is None:
            raise Exception("output buffer was not allocated")
        if status:
            print(f"Status: {status}")

        self._process_sound_queue()
        self._process_music_queue()

        self._output_buffer.fill(0.0)

        self._mix_sounds(self._output_buffer, frames)

        self._mix_music(self._output_buffer, frames)

        if self.master_volume != 1.0:
            multiply(self._output_buffer, self.master_volume, out=self._output_buffer)

        clip(self._output_buffer, -0.95, 0.95, out=self._output_buffer)

        outdata[:] = self._output_buffer

    def _process_sound_queue(self) -> None:
        """Process sound queue"""
        sounds_to_play = []
        try:
            while True:
                sounds_to_play.append(self.sound_queue.get_nowait())
        except queue.Empty:
            pass

        for sound_name in sounds_to_play:
            if sound_name in self.sounds:
                self.sounds[sound_name].play()

    def _process_music_queue(self) -> None:
        """Process music queue"""
        music_commands = []
        try:
            while True:
                music_commands.append(self.music_queue.get_nowait())
        except queue.Empty:
            pass

        for command in music_commands:
            music_name, action, *args = command
            if music_name in self.music_streams:
                music = self.music_streams[music_name]
                if action == 'play':
                    music.play()
                elif action == 'stop':
                    music.stop()
                elif action == 'pause':
                    music.pause()
                elif action == 'resume':
                    music.resume()
                elif action == 'seek' and args:
                    music.seek(args[0])

    def _mix_sounds(self, output: ndarray, frames: int) -> None:
        """sound mixing"""
        for sound in self.sounds.values():
            if not sound.is_playing:
                continue

            sound_data = sound.get_frames(frames)
            if sound_data is None or not isinstance(sound_data, ndarray):
                continue

            # Handle channel mismatch
            if sound.channels != self.output_channels:
                sound_data = self._convert_channels(sound_data, sound.channels)

            output += sound_data

    def _mix_music(self, output: ndarray, frames: int) -> None:
        """music mixing"""
        for music in self.music_streams.values():
            if not music.is_playing:
                continue

            music_data = music.get_frames(frames)
            if music_data is None:
                continue

            if music.channels != self.output_channels:
                music_data = self._convert_channels(music_data, music.channels)

            output += music_data

    def _convert_channels(self, data: ndarray, input_channels: int) -> ndarray:
        """Channel conversion using single pre-allocated buffer"""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
            input_channels = 1

        frames = data.shape[0]

        if input_channels == self.output_channels:
            return data

        if self._channel_conversion_buffer is None:
            raise Exception("channel conversion buffer was not allocated")

        self._channel_conversion_buffer[:frames, :self.output_channels].fill(0.0)

        if input_channels == 1 and self.output_channels > 1:
            # Mono to stereo/multi: broadcast to all channels
            for ch in range(self.output_channels):
                self._channel_conversion_buffer[:frames, ch] = data[:frames, 0]

        elif input_channels > self.output_channels:
            if self.output_channels == 1:
                # Multi to mono: average channels
                self._channel_conversion_buffer[:frames, 0] = mean(data[:frames, :input_channels], axis=1)
            else:
                # Multi to fewer channels: take first N channels
                self._channel_conversion_buffer[:frames, :self.output_channels] = data[:frames, :self.output_channels]

        # Return a view of the converted data
        return self._channel_conversion_buffer[:frames, :self.output_channels]

    def _start_update_thread(self) -> None:
        """Start a thread to update music streams"""
        self.update_thread_running = True
        self.update_thread = Thread(target=self._update_music_thread)
        self.update_thread.daemon = True
        self.update_thread.start()

    def _update_music_thread(self) -> None:
        """Thread function to update all music streams"""
        while self.update_thread_running:
            active_streams = [music for music in self.music_streams.values() if music.is_playing]

            if not active_streams:
                time.sleep(0.5)
                continue

            for music in active_streams:
                music.update()

            time.sleep(0.1)

    def init_audio_device(self):
        if self.audio_device_ready:
            return True

        try:
            self._initialize_api()

            self._expected_frames = self.buffer_size
            self._output_buffer = zeros((self._expected_frames, self.output_channels), dtype=float32)
            self._channel_conversion_buffer = zeros((self._expected_frames, max(8, self.output_channels)), dtype=float32)
            # Set up and start the stream
            extra_settings = None
            buffer_size = self.buffer_size
            self.stream = sd.OutputStream(
                samplerate=self.target_sample_rate,
                channels=self.output_channels,
                callback=self._audio_callback,
                blocksize=buffer_size,
                device=self.device_id,
                latency='low',
                extra_settings=extra_settings
            )
            self.stream.start()
            self.running = True
            self.audio_device_ready = True

            # Start update thread for music streams
            self._start_update_thread()

            print(f"Audio device initialized with {self.output_channels} channels at {self.target_sample_rate}Hz")
            return True
        except Exception as e:
            print(f"Error initializing audio device: {e}")
            self.audio_device_ready = False
            return False

    def close_audio_device(self) -> None:
        self.update_thread_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.running = False
        self.audio_device_ready = False
        self.sounds = {}
        self.music_streams = {}
        self.sound_queue = queue.Queue()
        self.music_queue = queue.Queue()
        self._output_buffer = None
        self._channel_conversion_buffer = None
        print("Audio device closed")
        return

    def is_audio_device_ready(self) -> bool:
        return self.audio_device_ready

    def set_master_volume(self, volume: float):
        self.master_volume = max(0.0, min(1.0, volume))

    def get_master_volume(self) -> float:
        return self.master_volume

    def load_sound(self, fileName: Path) -> str:
        sound = Sound(fileName, target_sample_rate=self.target_sample_rate)
        sound_id = f"sound_{len(self.sounds)}"
        self.sounds[sound_id] = sound
        print(f"Loaded sound from {fileName} as {sound_id}")
        return sound_id

    def play_sound(self, sound) -> None:
        if sound in self.sounds:
            self.sound_queue.put(sound)

    def stop_sound(self, sound) -> None:
        if sound in self.sounds:
            self.sounds[sound].stop()

    def pause_sound(self, sound: str) -> None:
        if sound in self.sounds:
            self.sounds[sound].pause()

    def resume_sound(self, sound: str) -> None:
        if sound in self.sounds:
            self.sounds[sound].resume()

    def unload_sound(self, sound: str) -> None:
        if sound in self.sounds:
            del self.sounds[sound]

    def unload_all_sounds(self) -> None:
        sounds_to_clear = list(self.sounds.keys())
        for key in sounds_to_clear:
            if key in self.sounds:
                del self.sounds[key]

    def normalize_sound(self, sound: str, rms: float) -> None:
        if sound in self.sounds:
            self.sounds[sound].normalize_vol(rms)

    def is_sound_valid(self, sound: str) -> bool:
        return sound in self.music_streams

    def is_sound_playing(self, sound: str) -> bool:
        if sound in self.sounds:
            return self.sounds[sound].is_playing
        return False

    def set_sound_volume(self, sound: str, volume: float) -> None:
        if sound in self.sounds:
            self.sounds[sound].volume = max(0.0, volume)

    def set_sound_pan(self, sound: str, pan: float) -> None:
        if sound in self.sounds:
            self.sounds[sound].pan = max(0.0, min(1.0, pan))

    def load_music_stream(self, fileName: Path, preview: float=0, normalize: Optional[float] = None) -> str:
        music = Music(file_path=fileName, target_sample_rate=self.target_sample_rate, preview=preview, normalize=normalize)
        music_id = f"music_{len(self.music_streams)}"
        self.music_streams[music_id] = music
        print(f"Loaded music stream from {fileName} as {music_id}")
        return music_id

    def load_music_stream_from_data(self, audio_array: ndarray, sample_rate: int=44100) -> str:
        """Load music stream from numpy array data"""
        # Create a dummy path since Music class expects one
        dummy_path = Path("memory_audio")
        music = Music(file_path=dummy_path, data=audio_array, target_sample_rate=self.target_sample_rate, sample_rate=sample_rate)
        music_id = f"music_{len(self.music_streams)}"
        self.music_streams[music_id] = music
        print(f"Loaded music stream from memory data as {music_id}")
        return music_id

    def is_music_valid(self, music: str) -> bool:
        if music in self.music_streams:
            return self.music_streams[music].valid
        return False

    def unload_music_stream(self, music: str) -> None:
        if music in self.music_streams:
            del self.music_streams[music]

    def play_music_stream(self, music: str) -> None:
        if music in self.music_streams:
            self.music_queue.put((music, 'play'))

    def is_music_stream_playing(self, music: str) -> bool:
        if music in self.music_streams:
            return self.music_streams[music].is_playing
        return False

    def update_music_stream(self, music: str) -> None:
        if music in self.music_streams:
            self.music_streams[music].update()

    def stop_music_stream(self, music: str) -> None:
        if music in self.music_streams:
            self.music_queue.put((music, 'stop'))

    def pause_music_stream(self, music: str) -> None:
        if music in self.music_streams:
            self.music_queue.put((music, 'pause'))

    def resume_music_stream(self, music: str) -> None:
        if music in self.music_streams:
            self.music_queue.put((music, 'resume'))

    def seek_music_stream(self, music: str, position: float) -> None:
        if music in self.music_streams:
            self.music_queue.put((music, 'seek', position))

    def set_music_volume(self, music: str, volume: float) -> None:
        if music in self.music_streams:
            self.music_streams[music].volume = max(0.0, min(1.0, volume))

    def set_music_pan(self, music: str, pan: float) -> None:
        if music in self.music_streams:
            self.music_streams[music].pan = max(0.0, min(1.0, pan))

    def normalize_music_stream(self, music: str, rms: float) -> None:
        if music in self.music_streams:
            self.music_streams[music].normalize = rms

    def get_music_time_length(self, music: str) -> float:
        if music in self.music_streams:
            return self.music_streams[music].get_time_length()
        raise ValueError(f"Music stream {music} not initialized")

    def get_music_time_played(self, music: str) -> float:
        if music in self.music_streams:
            return self.music_streams[music].get_time_played()
        raise ValueError(f"Music stream {music} not initialized")

audio = AudioEngine(get_config()["audio"]["device_type"])
