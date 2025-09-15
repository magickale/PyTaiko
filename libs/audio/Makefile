# Makefile for audio library with full static linking
CC = gcc
CFLAGS = -Wall -Wextra -O3 -fPIC -std=c99
LDFLAGS = -shared -Wl,--export-dynamic
LIBS = -lportaudio -lsndfile -lsamplerate -lpthread -lm
UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)

# MSYS2/MinGW-w64 with full static linking
ifneq (,$(findstring MINGW,$(UNAME_S)))
    CC = x86_64-w64-mingw32-gcc
    LIBNAME = libaudio.dll
    CFLAGS = -Wall -Wextra -O3 -fPIC -std=c99 -I/mingw64/include -m64

    # Full static linking flags
    LDFLAGS = -shared \
              -Wl,--export-all-symbols \
              -Wl,--whole-archive \
              -static-libgcc \
              -static-libstdc++ \
              -static \
              -L/mingw64/lib \
              -m64

    # Static libraries in correct order (dependencies matter!)
    LIBS = -Wl,--start-group \
           -lportaudio \
           -lsndfile \
           -lsamplerate \
           -lFLAC \
           -lvorbisenc \
           -lvorbisfile \
           -lvorbis \
           -logg \
           -lopus \
           -lwinmm \
           -lole32 \
           -luuid \
           -lksuser \
           -lsetupapi \
           -lws2_32 \
           -ladvapi32 \
           -luser32 \
           -lgdi32 \
           -lkernel32 \
           -Wl,--end-group \
           -Wl,--no-whole-archive

    OBJ_EXT = .o

else ifneq (,$(findstring Windows,$(UNAME_S)))
    # Windows with MSVC (alternative approach)
    CC = cl
    LIBNAME = libaudio.dll
    CFLAGS = /O2 /W3 /MD /TC /DSTATIC_LINK
    LDFLAGS = /DLL /NODEFAULTLIB:MSVCRT
    LIBS = portaudio_static.lib libsndfile_static.lib libsamplerate_static.lib \
           winmm.lib ole32.lib uuid.lib setupapi.lib ws2_32.lib
    OBJ_EXT = .obj

else ifeq ($(UNAME_S),Darwin)
    # macOS with static linking
    LIBNAME = libaudio.dylib
    CFLAGS += -I/usr/local/include -I/opt/homebrew/include
    LDFLAGS = -shared -undefined dynamic_lookup
    LDFLAGS += -L/usr/local/lib -L/opt/homebrew/lib
    # Try static first, fall back to dynamic
    LIBS = -Wl,-search_paths_first \
           /usr/local/lib/libportaudio.a \
           /usr/local/lib/libsndfile.a \
           /usr/local/lib/libsamplerate.a \
           -framework CoreAudio -framework AudioToolbox -framework AudioUnit \
           -framework CoreFoundation -framework CoreServices
    OBJ_EXT = .o

else ifeq ($(UNAME_S),Linux)
    # Linux with static linking
    LIBNAME = libaudio.so
    LDFLAGS = -shared -static-libgcc
    # Static link audio libraries, dynamic link system libraries
    LIBS = -Wl,-Bstatic \
           -lportaudio \
           -lsndfile \
           -lsamplerate \
           -lFLAC \
           -lvorbisenc \
           -lvorbisfile \
           -lvorbis \
           -logg \
           -Wl,-Bdynamic \
           -lasound \
           -ljack \
           -lpulse \
           -lpulse-simple \
           -pthread \
           -lm \
           -ldl
    OBJ_EXT = .o

else
    # Generic Unix fallback
    LIBNAME = libaudio.so
    OBJ_EXT = .o
endif

SOURCES = $(wildcard *.c)

# Object files with correct extension
ifneq (,$(findstring Windows,$(UNAME_S)))
    OBJECTS = $(SOURCES:.c=.obj)
else
    OBJECTS = $(SOURCES:.c=.o)
endif

.PHONY: all clean install debug check-deps static

all: $(LIBNAME)

# Main build targets
ifneq (,$(findstring Windows,$(UNAME_S)))
$(LIBNAME): $(OBJECTS)
	link $(LDFLAGS) /OUT:$@ $^ $(LIBS)

%.obj: %.c
	$(CC) $(CFLAGS) /c $< /Fo:$@

clean:
	-del /Q *.obj $(LIBNAME) 2>nul || rm -f $(OBJECTS) $(LIBNAME)

check-deps:
	@echo "Checking for static libraries on Windows..."
	@if exist "$(VCPKG_INSTALLATION_ROOT)\installed\x64-windows-static\lib\portaudio.lib" (echo Static PortAudio found!) else (echo Static PortAudio not found!)

else
# Unix/Linux/macOS build rules
$(LIBNAME): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $^ $(LIBS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(LIBNAME)

install: $(LIBNAME)
	sudo cp $(LIBNAME) /usr/local/lib/
	sudo ldconfig 2>/dev/null || true

check-deps:
	@echo "Checking for static libraries..."
	@pkg-config --exists --static portaudio-2.0 || echo "Static PortAudio not found"
	@pkg-config --exists --static sndfile || echo "Static libsndfile not found"
	@find /usr/local/lib /usr/lib -name "libportaudio.a" 2>/dev/null || echo "No static portaudio found"
	@find /usr/local/lib /usr/lib -name "libsndfile.a" 2>/dev/null || echo "No static sndfile found"

endif

# Development target with debug symbols
debug: CFLAGS += $(if $(findstring Windows,$(UNAME_S)),/Zi,-g -DDEBUG)
debug: $(LIBNAME)

# Target to build with maximum static linking
static: LDFLAGS += $(if $(findstring MINGW,$(UNAME_S)),-static,)
static: $(LIBNAME)

# Verification target
verify: $(LIBNAME)
	@echo "=== Library Information ==="
	@if [ "$(findstring MINGW,$(UNAME_S))" ]; then \
		file $(LIBNAME); \
		echo "=== Dependencies ==="; \
		objdump -p $(LIBNAME) | grep "DLL Name:" || echo "No DLL dependencies (fully static)"; \
	elif [ "$(UNAME_S)" = "Linux" ]; then \
		file $(LIBNAME); \
		echo "=== Dependencies ==="; \
		ldd $(LIBNAME) 2>/dev/null || echo "No shared library dependencies"; \
	else \
		file $(LIBNAME); \
	fi

help:
	@echo "Available targets:"
	@echo "  all       - Build the audio library (default)"
	@echo "  static    - Build with maximum static linking"
	@echo "  clean     - Remove build artifacts"
	@echo "  install   - Install library (Unix/Linux/macOS only)"
	@echo "  debug     - Build with debug symbols"
	@echo "  check-deps- Check for required dependencies"
	@echo "  verify    - Verify built library and show dependencies"
	@echo "  help      - Show this help message"
