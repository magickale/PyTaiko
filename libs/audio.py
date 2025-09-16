import cffi
import platform
from pathlib import Path
from typing import Optional
import numpy as np

from libs.utils import get_config

# Initialize CFFI
ffi = cffi.FFI()

# Define the C interface
ffi.cdef("""
    typedef int PaHostApiIndex;
    // Forward declarations
    struct audio_buffer;

    // Type definitions
    typedef struct wave {
        unsigned int frameCount;
        unsigned int sampleRate;
        unsigned int sampleSize;
        unsigned int channels;
        void *data;
    } wave;

    typedef struct audio_stream {
        struct audio_buffer *buffer;
        unsigned int sampleRate;
        unsigned int sampleSize;
        unsigned int channels;
    } audio_stream;

    typedef struct sound {
        audio_stream stream;
        unsigned int frameCount;
    } sound;

    typedef struct music {
        audio_stream stream;
        unsigned int frameCount;
        void *ctxData;
    } music;

    // Device management
    void list_host_apis(void);
    void init_audio_device(PaHostApiIndex host_api, double sample_rate);
    void close_audio_device(void);
    bool is_audio_device_ready(void);
    void set_master_volume(float volume);
    float get_master_volume(void);

    // Wave management
    wave load_wave(const char* filename);
    bool is_wave_valid(wave wave);
    void unload_wave(wave wave);

    // Sound management
    sound load_sound_from_wave(wave wave);
    sound load_sound(const char* filename);
    bool is_sound_valid(sound sound);
    void unload_sound(sound sound);
    void play_sound(sound sound);
    void pause_sound(sound sound);
    void resume_sound(sound sound);
    void stop_sound(sound sound);
    bool is_sound_playing(sound sound);
    void set_sound_volume(sound sound, float volume);
    void set_sound_pitch(sound sound, float pitch);
    void set_sound_pan(sound sound, float pan);

    // Audio stream management
    audio_stream load_audio_stream(unsigned int sample_rate, unsigned int sample_size, unsigned int channels);
    void unload_audio_stream(audio_stream stream);
    void play_audio_stream(audio_stream stream);
    void pause_audio_stream(audio_stream stream);
    void resume_audio_stream(audio_stream stream);
    bool is_audio_stream_playing(audio_stream stream);
    void stop_audio_stream(audio_stream stream);
    void set_audio_stream_volume(audio_stream stream, float volume);
    void set_audio_stream_pitch(audio_stream stream, float pitch);
    void set_audio_stream_pan(audio_stream stream, float pan);
    void update_audio_stream(audio_stream stream, const void *data, int frame_count);

    // Music management
    music load_music_stream(const char* filename);
    bool is_music_valid(music music);
    void unload_music_stream(music music);
    void play_music_stream(music music);
    void pause_music_stream(music music);
    void resume_music_stream(music music);
    void stop_music_stream(music music);
    void seek_music_stream(music music, float position);
    void update_music_stream(music music);
    bool is_music_stream_playing(music music);
    void set_music_volume(music music, float volume);
    void set_music_pitch(music music, float pitch);
    void set_music_pan(music music, float pan);
    float get_music_time_length(music music);
    float get_music_time_played(music music);

    // Memory management
    void free(void *ptr);
""")

# Load the compiled C library
# gcc -shared -fPIC -o libaudio.so audio.c -lportaudio -lsndfile -lpthread
try:
    if platform.system() == "Windows":
        lib = ffi.dlopen("libaudio.dll")  # or "libaudio.dll" if that's the compiled name
    elif platform.system() == "Darwin":
        lib = ffi.dlopen("./libaudio.dylib")
    else:  # Assume Linux/Unix
        lib = ffi.dlopen("./libaudio.so")
except OSError as e:
    print(f"Failed to load shared library: {e}")
    print("Make sure to compile your C code first.")
    if platform.system() == "Linux":
        print("Example:")
        print("gcc -shared -fPIC -o libaudio.so audio.c -lportaudio -lsndfile -lpthread")
    elif platform.system() == "Windows":
        print("On Windows, make sure you've built a DLL with MinGW or MSVC:")
        print("Example with MinGW:")
        print("gcc -shared -o libaudio.dll audio.c -lportaudio -lsndfile -lpthread")
    elif platform.system() == "Darwin":
        print("On macOS:")
        print("gcc -dynamiclib -o libaudio.dylib audio.c -lportaudio -lsndfile -lpthread")
    raise

class AudioEngine:
    def __init__(self, device_type: int, sample_rate: float):
        self.device_type = device_type
        if sample_rate == -1:
            sample_rate = 44100
        self.target_sample_rate = sample_rate
        self.sounds = {}  # sound_id -> sound struct
        self.music_streams = {}  # music_id -> music struct
        self.sound_counter = 0
        self.music_counter = 0
        self.audio_device_ready = False

    def list_host_apis(self):
        lib.list_host_apis()

    def init_audio_device(self) -> bool:
        """Initialize the audio device"""
        try:
            lib.init_audio_device(self.device_type, self.target_sample_rate)
            self.audio_device_ready = lib.is_audio_device_ready()
            if self.audio_device_ready:
                print("Audio device initialized successfully")
            return self.audio_device_ready
        except Exception as e:
            print(f"Failed to initialize audio device: {e}")
            return False

    def close_audio_device(self) -> None:
        """Close the audio device"""
        try:
            # Clean up all sounds and music
            for sound_id in list(self.sounds.keys()):
                self.unload_sound(sound_id)
            for music_id in list(self.music_streams.keys()):
                self.unload_music_stream(music_id)

            lib.close_audio_device()
            self.audio_device_ready = False
            print("Audio device closed")
        except Exception as e:
            print(f"Error closing audio device: {e}")

    def is_audio_device_ready(self) -> bool:
        """Check if audio device is ready"""
        return lib.is_audio_device_ready()

    def set_master_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)"""
        lib.set_master_volume(max(0.0, min(1.0, volume)))

    def get_master_volume(self) -> float:
        """Get master volume"""
        return lib.get_master_volume()

    # Sound management
    def load_sound(self, file_path: Path) -> str:
        """Load a sound file and return sound ID"""
        try:
            file_path_str = str(file_path).encode('utf-8')
            sound = lib.load_sound(file_path_str)

            if lib.is_sound_valid(sound):
                sound_id = f"sound_{self.sound_counter}"
                self.sounds[sound_id] = sound
                self.sound_counter += 1
                print(f"Loaded sound from {file_path} as {sound_id}")
                return sound_id
            else:
                print(f"Failed to load sound: {file_path}")
                return ""
        except Exception as e:
            print(f"Error loading sound {file_path}: {e}")
            return ""

    def unload_sound(self, sound_id: str) -> None:
        """Unload a sound"""
        if sound_id in self.sounds:
            lib.unload_sound(self.sounds[sound_id])
            del self.sounds[sound_id]

    def unload_all_sounds(self) -> None:
        """Unload all sounds"""
        for sound_id in list(self.sounds.keys()):
            self.unload_sound(sound_id)

    def play_sound(self, sound_id: str) -> None:
        """Play a sound"""
        if sound_id in self.sounds:
            lib.play_sound(self.sounds[sound_id])

    def stop_sound(self, sound_id: str) -> None:
        """Stop a sound"""
        if sound_id in self.sounds:
            lib.stop_sound(self.sounds[sound_id])

    def pause_sound(self, sound_id: str) -> None:
        """Pause a sound"""
        if sound_id in self.sounds:
            lib.pause_sound(self.sounds[sound_id])

    def resume_sound(self, sound_id: str) -> None:
        """Resume a sound"""
        if sound_id in self.sounds:
            lib.resume_sound(self.sounds[sound_id])

    def is_sound_valid(self, sound_id: str) -> bool:
        """Check if sound is valid"""
        if sound_id in self.sounds:
            return lib.is_sound_valid(self.sounds[sound_id])
        return False

    def is_sound_playing(self, sound_id: str) -> bool:
        """Check if sound is playing"""
        if sound_id in self.sounds:
            return lib.is_sound_playing(self.sounds[sound_id])
        return False

    def set_sound_volume(self, sound_id: str, volume: float) -> None:
        """Set sound volume"""
        if sound_id in self.sounds:
            lib.set_sound_volume(self.sounds[sound_id], max(0.0, volume))

    def set_sound_pan(self, sound_id: str, pan: float) -> None:
        """Set sound pan (0.0 = left, 0.5 = center, 1.0 = right)"""
        if sound_id in self.sounds:
            lib.set_sound_pan(self.sounds[sound_id], max(0.0, min(1.0, pan)))

    def normalize_sound(self, sound_id: str, rms: float) -> None:
        """Normalize sound - Note: This would need to be implemented in C"""
        # The C implementation doesn't have normalize function yet
        # You'd need to add this to your C code
        print(f"Warning: normalize_sound not implemented in C backend")

    # Music management
    def load_music_stream(self, file_path: Path, normalize: Optional[float] = None) -> str:
        """Load a music stream and return music ID"""
        try:
            file_path_str = str(file_path).encode('utf-8')
            music = lib.load_music_stream(file_path_str)

            if lib.is_music_valid(music):
                music_id = f"music_{self.music_counter}"
                self.music_streams[music_id] = music
                self.music_counter += 1
                print(f"Loaded music stream from {file_path} as {music_id}")
                return music_id
            else:
                print(f"Failed to load music: {file_path}")
                return ""
        except Exception as e:
            print(f"Error loading music {file_path}: {e}")
            return ""

    def load_music_stream_from_data(self, audio_array: np.ndarray, sample_rate: int = 44100) -> str:
        """Load music from numpy array - would need C implementation"""
        print("Warning: load_music_stream_from_data not implemented in C backend")
        return ""

    def unload_music_stream(self, music_id: str) -> None:
        """Unload a music stream"""
        if music_id in self.music_streams:
            lib.unload_music_stream(self.music_streams[music_id])
            del self.music_streams[music_id]

    def is_music_valid(self, music_id: str) -> bool:
        """Check if music is valid"""
        if music_id in self.music_streams:
            return lib.is_music_valid(self.music_streams[music_id])
        return False

    def play_music_stream(self, music_id: str) -> None:
        """Play a music stream"""
        if music_id in self.music_streams:
            lib.play_music_stream(self.music_streams[music_id])

    def stop_music_stream(self, music_id: str) -> None:
        """Stop a music stream"""
        if music_id in self.music_streams:
            lib.stop_music_stream(self.music_streams[music_id])

    def pause_music_stream(self, music_id: str) -> None:
        """Pause a music stream"""
        if music_id in self.music_streams:
            lib.pause_music_stream(self.music_streams[music_id])

    def resume_music_stream(self, music_id: str) -> None:
        """Resume a music stream"""
        if music_id in self.music_streams:
            lib.resume_music_stream(self.music_streams[music_id])

    def is_music_stream_playing(self, music_id: str) -> bool:
        """Check if music stream is playing"""
        if music_id in self.music_streams:
            return lib.is_music_stream_playing(self.music_streams[music_id])
        return False

    def seek_music_stream(self, music_id: str, position: float) -> None:
        """Seek music stream to position in seconds"""
        if music_id in self.music_streams:
            lib.seek_music_stream(self.music_streams[music_id], position)

    def update_music_stream(self, music_id: str) -> None:
        """Update music stream (fill buffers)"""
        if music_id in self.music_streams:
            lib.update_music_stream(self.music_streams[music_id])

    def set_music_volume(self, music_id: str, volume: float) -> None:
        """Set music volume"""
        if music_id in self.music_streams:
            lib.set_music_volume(self.music_streams[music_id], max(0.0, min(1.0, volume)))

    def set_music_pan(self, music_id: str, pan: float) -> None:
        """Set music pan"""
        if music_id in self.music_streams:
            lib.set_music_pan(self.music_streams[music_id], max(0.0, min(1.0, pan)))

    def normalize_music_stream(self, music_id: str, rms: float) -> None:
        """Normalize music stream - would need C implementation"""
        print("Warning: normalize_music_stream not implemented in C backend")

    def get_music_time_length(self, music_id: str) -> float:
        """Get total music length in seconds"""
        if music_id in self.music_streams:
            return lib.get_music_time_length(self.music_streams[music_id])
        return 0.0

    def get_music_time_played(self, music_id: str) -> float:
        """Get current music position in seconds"""
        if music_id in self.music_streams:
            return lib.get_music_time_played(self.music_streams[music_id])
        return 0.0

# Create the global audio instance
audio = AudioEngine(get_config()["audio"]["device_type"], get_config()["audio"]["sample_rate"])
