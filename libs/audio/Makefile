# Makefile for audio library
# Default compiler and flags for Unix-like systems
CC = gcc
CFLAGS = -Wall -Wextra -O3 -fPIC -std=c99
LDFLAGS = -shared -Wl,--export-dynamic
LIBS = -lportaudio -lsndfile -lsamplerate -lpthread -lm

# Detect OS and set appropriate flags
UNAME_S := $(shell uname -s 2>/dev/null || echo Windows)

# Windows detection (including GitHub Actions Windows runners)
ifneq (,$(findstring Windows,$(UNAME_S)))
    # Windows with MSVC
    CC = cl
    LIBNAME = libaudio.dll
    CFLAGS = /O2 /W3 /MD /TC
    LDFLAGS = /DLL
    LIBS = portaudio.lib libsndfile.lib libsamplerate.lib
    OBJ_EXT = .obj

    # Check for vcpkg environment
    ifdef VCPKG_INSTALLATION_ROOT
        INCLUDE_PATH = /I"$(VCPKG_INSTALLATION_ROOT)/installed/x64-windows/include"
        LIB_PATH = /LIBPATH:"$(VCPKG_INSTALLATION_ROOT)/installed/x64-windows/lib"
        CFLAGS += $(INCLUDE_PATH)
        LDFLAGS += $(LIB_PATH)
    endif

    # Check for environment variables set by GitHub Actions
    ifdef VCPKG_INCLUDE_PATH
        CFLAGS += /I"$(VCPKG_INCLUDE_PATH)"
    endif
    ifdef VCPKG_LIB_PATH
        LDFLAGS += /LIBPATH:"$(VCPKG_LIB_PATH)"
    endif

else ifeq ($(UNAME_S),Darwin)
    # macOS
    LIBNAME = libaudio.dylib
    CFLAGS += -I/usr/local/include -I/opt/homebrew/include
    LDFLAGS = -shared -undefined dynamic_lookup
    LDFLAGS += -L/usr/local/lib -L/opt/homebrew/lib
    OBJ_EXT = .o

else ifeq ($(UNAME_S),Linux)
    # Linux
    LIBNAME = libaudio.so
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

.PHONY: all clean install debug check-deps

all: $(LIBNAME)

# Windows-specific build rule
ifneq (,$(findstring Windows,$(UNAME_S)))
$(LIBNAME): $(OBJECTS)
	link $(LDFLAGS) /OUT:$@ $^ $(LIBS)

%.obj: %.c
	$(CC) $(CFLAGS) /c $< /Fo:$@

clean:
	-del /Q *.obj $(LIBNAME) 2>nul || rm -f $(OBJECTS) $(LIBNAME)

install:
	@echo "Install not implemented for Windows. Copy $(LIBNAME) to your application directory."

check-deps:
	@echo "Checking dependencies on Windows..."
	@echo "Assuming vcpkg dependencies are installed..."
	@if exist "$(VCPKG_INSTALLATION_ROOT)\installed\x64-windows\include\portaudio.h" (echo PortAudio found!) else (echo PortAudio not found! && exit 1)
	@if exist "$(VCPKG_INSTALLATION_ROOT)\installed\x64-windows\include\sndfile.h" (echo libsndfile found!) else (echo libsndfile not found! && exit 1)
	@echo "All dependencies found!"

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
	@echo "Checking dependencies..."
	@pkg-config --exists portaudio-2.0 || (echo "PortAudio not found!" && false)
	@pkg-config --exists sndfile || (echo "libsndfile not found!" && false)
	@echo "All dependencies found!"

endif

# Development target with debug symbols (cross-platform)
debug: CFLAGS += $(if $(findstring Windows,$(UNAME_S)),/Zi,-g -DDEBUG)
debug: $(LIBNAME)

# Help target
help:
	@echo "Available targets:"
	@echo "  all       - Build the audio library (default)"
	@echo "  clean     - Remove build artifacts"
	@echo "  install   - Install library (Unix/Linux/macOS only)"
	@echo "  debug     - Build with debug symbols"
	@echo "  check-deps- Check for required dependencies"
	@echo "  help      - Show this help message"
