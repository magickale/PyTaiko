import io
import os
import queue
import time
import wave
from threading import Lock, Thread

from numpy import (
    abs as np_abs,
)
from numpy import (
    arange,
    column_stack,
    float32,
    frombuffer,
    int16,
    int32,
    interp,
    mean,
    uint8,
    zeros,
)
from numpy import (
    max as np_max,
)

os.environ["SD_ENABLE_ASIO"] = "1"
import sounddevice as sd
from pydub import AudioSegment

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

class Sound:
    def __init__(self, file_path, data=None, target_sample_rate=44100):
        self.file_path = file_path
        self.data = data
        self.channels = 0
        self.sample_rate = target_sample_rate
        self.position = 0
        self.is_playing = False
        self.is_paused = False
        self.volume = 1.0
        self.pan = 0.5  # 0.0 = left, 0.5 = center, 1.0 = right

        if file_path:
            self.load()

    def load(self):
        """Load and prepare the sound file data"""
        if self.file_path.endswith('.ogg'):
            audio = AudioSegment.from_ogg(self.file_path)
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_io.seek(0)
            file_path = wav_io
        else:
            file_path = self.file_path
        with wave.open(file_path, 'rb') as wf:
            # Get file properties
            self.channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            original_sample_rate = wf.getframerate()
            frames = wf.getnframes()

            # Read all frames from the file
            raw_data = wf.readframes(frames)

            data = get_np_array(sample_width, raw_data)

            # Reshape for multi-channel audio
            if self.channels > 1:
                data = data.reshape(-1, self.channels)

            # Resample if needed
            if original_sample_rate != self.sample_rate:
                print(f"Resampling {self.file_path} from {original_sample_rate}Hz to {self.sample_rate}Hz")
                data = resample(data, original_sample_rate, self.sample_rate)

            self.data = data

    def play(self):
        self.position = 0
        self.is_playing = True
        self.is_paused = False

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        self.position = 0

    def pause(self):
        if self.is_playing:
            self.is_paused = True
            self.is_playing = False

    def resume(self):
        if self.is_paused:
            self.is_playing = True
            self.is_paused = False

    def get_frames(self, num_frames):
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
            output[:frames_to_get] = self.data[self.position:self.position+frames_to_get]
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
    def __init__(self, file_path, data=None, file_type=None, target_sample_rate=44100):
        self.file_path = file_path
        self.file_type = file_type
        self.data = data
        self.target_sample_rate = target_sample_rate
        self.sample_rate = target_sample_rate
        self.channels = 0
        self.position = 0  # In frames
        self.is_playing = False
        self.is_paused = False
        self.volume = 1.0
        self.pan = 0.5  # Center
        self.total_frames = 0
        self.valid = False

        self.wave_file = None
        self.file_buffer_size = int(target_sample_rate * 5)  # 5 seconds buffer
        self.buffer = None
        self.buffer_position = 0

        # Thread-safe updates
        self.lock = Lock()

        self.load_from_file()

    def load_from_file(self):
        """Load music from file"""
        if self.file_path.endswith('.ogg'):
            audio = AudioSegment.from_ogg(self.file_path)
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            wav_io.seek(0)
            file_path = wav_io
        else:
            file_path = self.file_path
        try:
            # Keep the file open for streaming
            self.wave_file = wave.open(file_path, 'rb')

            # Get file properties
            self.channels = self.wave_file.getnchannels()
            self.sample_width = self.wave_file.getsampwidth()
            self.sample_rate = self.wave_file.getframerate()
            self.total_frames = self.wave_file.getnframes()

            # Initialize buffer with some initial data
            self._fill_buffer()

            self.valid = True
            print(f"Music loaded: {self.channels} channels, {self.sample_rate}Hz, {self.total_frames} frames")
        except Exception as e:
            print(f"Error loading music file: {e}")
            if self.wave_file:
                self.wave_file.close()
                self.wave_file = None
            self.valid = False

    def _fill_buffer(self):
        """Fill the streaming buffer from file"""
        if not self.wave_file:
            return False

        # Read a chunk of frames from file
        try:
            frames_to_read = min(self.file_buffer_size, self.total_frames - self.position)
            if frames_to_read <= 0:
                return False

            raw_data = self.wave_file.readframes(frames_to_read)

            data = get_np_array(self.sample_width, raw_data)

            # Reshape for multi-channel audio
            if self.channels > 1:
                data = data.reshape(-1, self.channels)

            if self.sample_rate != self.target_sample_rate:
                print(f"Resampling {self.file_path} from {self.sample_rate}Hz to {self.target_sample_rate}Hz")
                data = resample(data, self.sample_rate, self.target_sample_rate)

            self.buffer = data
            self.buffer_position = 0
            return True
        except Exception as e:
            print(f"Error filling buffer: {e}")
            return False

    def update(self):
        """Update music stream buffers"""
        if not self.is_playing or self.is_paused:
            return

        with self.lock:
            # Check if we need to refill the buffer
            if self.buffer is None:
                raise Exception("buffer is None")
            if self.wave_file and self.buffer_position >= len(self.buffer):
                if not self._fill_buffer():
                    self.is_playing = False

    def play(self):
        """Start playing the music stream"""
        with self.lock:
            # Reset position if at the end
            if self.wave_file and self.position >= self.total_frames:
                self.wave_file.rewind()
                self.position = 0
                self.buffer_position = 0
                self._fill_buffer()

            self.is_playing = True
            self.is_paused = False

    def stop(self):
        """Stop playing the music stream"""
        with self.lock:
            self.is_playing = False
            self.is_paused = False
            self.position = 0
            self.buffer_position = 0
            if self.wave_file:
                self.wave_file.rewind()
                self._fill_buffer()

    def pause(self):
        """Pause the music playback"""
        with self.lock:
            if self.is_playing:
                self.is_paused = True
                self.is_playing = False

    def resume(self):
        """Resume the music playback"""
        with self.lock:
            if self.is_paused:
                self.is_playing = True
                self.is_paused = False

    def seek(self, position_seconds):
        """Seek to a specific position in seconds"""
        with self.lock:
            # Convert seconds to frames
            frame_position = int(position_seconds * self.sample_rate)

            # Clamp position to valid range
            frame_position = max(0, min(frame_position, self.total_frames - 1))

            # Update file position if streaming from file
            if self.wave_file:
                self.wave_file.setpos(frame_position)
                self._fill_buffer()

            self.position = frame_position
            self.buffer_position = 0

    def get_time_length(self):
        """Get the total length of the music in seconds"""
        return self.total_frames / self.sample_rate

    def get_time_played(self):
        """Get the current playback position in seconds"""
        return (self.position + self.buffer_position) / self.sample_rate

    def get_frames(self, num_frames):
        """Get the next num_frames of music data, applying volume, pitch, and pan"""
        if not self.is_playing:
            # Return silence if not playing
            if self.channels == 1:
                return zeros(num_frames, dtype=float32)
            else:
                return zeros((num_frames, self.channels), dtype=float32)

        with self.lock:
            if self.buffer is None:
                raise Exception("buffer is None")
            # Check if we need more data
            if self.buffer_position >= len(self.buffer):
                # If no more data available and streaming from file
                if self.wave_file and not self._fill_buffer():
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
                output[:frames_to_get] = self.buffer[self.buffer_position:self.buffer_position+frames_to_get]
            else:
                output = zeros((num_frames, self.channels), dtype=float32)
                output[:frames_to_get] = self.buffer[self.buffer_position:self.buffer_position+frames_to_get]

            # Update buffer position
            self.buffer_position += frames_to_get
            self.position += frames_to_get

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

    def __del__(self):
        """Cleanup when the music object is deleted"""
        if self.wave_file:
            try:
                self.wave_file.close()
            except Exception:
                raise Exception("unable to close music stream")

class AudioEngine:
    def __init__(self, type: str):
        self.target_sample_rate = 44100
        self.buffer_size = 10
        self.sounds = {}
        self.music_streams = {}
        self.stream = None
        self.device_id = None
        self.running = False
        self.sound_queue = queue.Queue()
        self.music_queue = queue.Queue()
        self.master_volume = 1.0
        self.output_channels = 2  # Default to stereo
        self.audio_device_ready = False

        # Threading for music stream updates
        self.update_thread = None
        self.update_thread_running = False
        self.type = type

    def _initialize_asio(self):
        """Set up ASIO device"""
        # Find ASIO API and use its default device
        hostapis = sd.query_hostapis()
        asio_api_index = -1
        for i, api in enumerate(hostapis):
            if isinstance(api, dict) and 'name' in api and api['name'] == self.type:
                asio_api_index = i
                break

        if isinstance(hostapis, tuple):
            asio_api = hostapis[asio_api_index]
            if isinstance(asio_api, dict) and 'default_output_device' in asio_api:
                default_asio_device = asio_api['default_output_device']
            else:
                raise Exception("Warning: 'default_output_device' key not found in ASIO API info.")
            if default_asio_device >= 0:
                self.device_id = default_asio_device
                device_info = sd.query_devices(self.device_id)
                if isinstance(device_info, sd.DeviceList):
                    raise Exception("Invalid ASIO Device")
                print(f"Using default ASIO device: {device_info['name']}")
                print(device_info)
                self.buffer_size = rounded(device_info['default_low_output_latency']*1000)
                if 'buffer_size' in get_config()['audio']:
                    self.buffer_size = get_config()['audio']['buffer_size']
                self.target_sample_rate = device_info['default_samplerate']
                if 'sample_rate' in get_config()['audio']:
                    self.target_sample_rate = get_config()['audio']['sample_rate']
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

    def _audio_callback(self, outdata, frames, time, status):
        """Callback function for the sounddevice stream"""
        if status:
            print(f"Status: {status}")

        # Process any new sound play requests
        while not self.sound_queue.empty():
            try:
                sound_name = self.sound_queue.get_nowait()
                if sound_name in self.sounds:
                    self.sounds[sound_name].play()
            except queue.Empty:
                break

        # Process any new music play requests
        while not self.music_queue.empty():
            try:
                music_name, action, *args = self.music_queue.get_nowait()
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
            except queue.Empty:
                break

        # Mix all playing sounds and music
        output = zeros((frames, self.output_channels), dtype=float32)

        # Mix sounds
        for sound_name, sound in self.sounds.items():
            if sound.is_playing:
                sound_data = sound.get_frames(frames)

                # If mono sound but stereo output, duplicate to both channels
                if sound.channels == 1 and self.output_channels > 1:
                    sound_data = column_stack([sound_data] * self.output_channels)

                # Ensure sound_data matches the output format
                if sound.channels > self.output_channels:
                    # Down-mix if needed
                    if self.output_channels == 1:
                        sound_data = mean(sound_data, axis=1)
                    else:
                        # Keep only the first output_channels
                        sound_data = sound_data[:, :self.output_channels]

                # Add to the mix (simple additive mixing)
                output += sound_data

        # Mix music streams
        for music_name, music in self.music_streams.items():
            if music.is_playing:
                music_data = music.get_frames(frames)

                # If mono music but stereo output, duplicate to both channels
                if music.channels == 1 and self.output_channels > 1:
                    music_data = column_stack([music_data] * self.output_channels)

                # Ensure music_data matches the output format
                if music.channels > self.output_channels:
                    # Down-mix if needed
                    if self.output_channels == 1:
                        music_data = mean(music_data, axis=1)
                    else:
                        # Keep only the first output_channels
                        music_data = music_data[:, :self.output_channels]

                # Add to the mix
                output += music_data

        # Apply master volume
        output *= self.master_volume

        # Apply simple limiter to prevent clipping
        max_val = np_max(np_abs(output))
        if max_val > 1.0:
            output = output / max_val

        outdata[:] = output

    def _start_update_thread(self):
        """Start a thread to update music streams"""
        self.update_thread_running = True
        self.update_thread = Thread(target=self._update_music_thread)
        self.update_thread.daemon = True
        self.update_thread.start()

    def _update_music_thread(self):
        """Thread function to update all music streams"""
        while self.update_thread_running:
            # Update all active music streams
            for music_name, music in self.music_streams.items():
                if music.is_playing:
                    music.update()

            # Sleep to not consume too much CPU
            time.sleep(0.1)

    def init_audio_device(self):
        if self.audio_device_ready:
            return True

        try:
            # Try to use ASIO if available
            self._initialize_asio()

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
            print(self.stream.samplerate, self.stream.blocksize, self.stream.latency*1000)

            # Start update thread for music streams
            self._start_update_thread()

            print(f"Audio device initialized with {self.output_channels} channels at {self.target_sample_rate}Hz")
            return True
        except Exception as e:
            print(f"Error initializing audio device: {e}")
            self.audio_device_ready = False
            return False

    def close_audio_device(self):
        self.update_thread_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        self.running = False
        self.audio_device_ready = False
        print("Audio device closed")
        return

    def is_audio_device_ready(self) -> bool:
        return self.audio_device_ready

    def set_master_volume(self, volume: float):
        self.master_volume = max(0.0, min(1.0, volume))

    def get_master_volume(self) -> float:
        return self.master_volume

    def load_sound(self, fileName: str) -> str:
        sound = Sound(fileName, target_sample_rate=self.target_sample_rate)
        sound_id = f"sound_{len(self.sounds)}"
        self.sounds[sound_id] = sound
        print(f"Loaded sound from {fileName} as {sound_id}")
        return sound_id

    def play_sound(self, sound):
        if sound in self.sounds:
            self.sound_queue.put(sound)

    def stop_sound(self, sound):
        if sound in self.sounds:
            self.sounds[sound].stop()

    def pause_sound(self, sound: str):
        if sound in self.sounds:
            self.sounds[sound].pause()

    def resume_sound(self, sound: str):
        if sound in self.sounds:
            self.sounds[sound].resume()

    def is_sound_playing(self, sound: str) -> bool:
        if sound in self.sounds:
            return self.sounds[sound].is_playing
        return False

    def set_sound_volume(self, sound: str, volume: float):
        if sound in self.sounds:
            self.sounds[sound].volume = max(0.0, min(1.0, volume))

    def set_sound_pan(self, sound: str, pan: float):
        if sound in self.sounds:
            self.sounds[sound].pan = max(0.0, min(1.0, pan))

    def load_music_stream(self, fileName: str) -> str:
        music = Music(file_path=fileName, target_sample_rate=self.target_sample_rate)
        music_id = f"music_{len(self.music_streams)}"
        self.music_streams[music_id] = music
        print(f"Loaded music stream from {fileName} as {music_id}")
        return music_id

    def is_music_valid(self, music: str) -> bool:
        if music in self.music_streams:
            return self.music_streams[music].valid
        return False

    def unload_music_stream(self, music: str):
        if music in self.music_streams:
            del self.music_streams[music]

    def play_music_stream(self, music: str):
        if music in self.music_streams:
            self.music_queue.put((music, 'play'))

    def is_music_stream_playing(self, music: str) -> bool:
        if music in self.music_streams:
            return self.music_streams[music].is_playing
        return False

    def update_music_stream(self, music: str):
        if music in self.music_streams:
            self.music_streams[music].update()

    def stop_music_stream(self, music: str):
        if music in self.music_streams:
            self.music_queue.put((music, 'stop'))

    def pause_music_stream(self, music: str):
        if music in self.music_streams:
            self.music_queue.put((music, 'pause'))

    def resume_music_stream(self, music: str):
        if music in self.music_streams:
            self.music_queue.put((music, 'resume'))

    def seek_music_stream(self, music: str, position: float):
        if music in self.music_streams:
            self.music_queue.put((music, 'seek', position))

    def set_music_volume(self, music: str, volume: float):
        if music in self.music_streams:
            self.music_streams[music].volume = max(0.0, min(1.0, volume))

    def set_music_pan(self, music: str, pan: float):
        if music in self.music_streams:
            self.music_streams[music].pan = max(0.0, min(1.0, pan))

    def get_music_time_length(self, music: str) -> float:
        if music in self.music_streams:
            return self.music_streams[music].get_time_length()
        raise ValueError(f"Music stream {music} not initialized")

    def get_music_time_played(self, music: str) -> float:
        if music in self.music_streams:
            return self.music_streams[music].get_time_played()
        raise ValueError(f"Music stream {music} not initialized")

audio = AudioEngine(get_config()["audio"]["device_type"])
audio.set_master_volume(0.75)
