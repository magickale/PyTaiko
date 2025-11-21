# PyTaiko

A TJA player and Taiko simulator written in Python using the [raylib](https://www.raylib.com/) library.

![License](https://img.shields.io/github/license/Yonokid/PyTaiko)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
[![GitHub Releases Downloads](https://img.shields.io/github/downloads/Yonokid/PyTaiko/total)](https://github.com/Yonokid/PyTaiko/releases)
[![GitHub Stars](https://img.shields.io/github/stars/Yonokid/PyTaiko?style=flat&label=stars)](https://github.com/Yonokid/PyTaiko/stargazers)
[![Discord Members](https://img.shields.io/discord/722513061419810946.svg?label=Discord&logo=discord)](https://discord.gg/XHcVYKW)
[![Builds](https://github.com/Yonokid/PyTaiko/actions/workflows/python-app.yml/badge.svg)](https://github.com/Yonokid/PyTaiko/actions/workflows/python-app.yml)

<img src="/docs/demo.gif">

## Features

- Cross-platform compatibility (Windows, macOS, Linux)
- Controller Support
- Low latency audio via ASIO
- Recursive Song Select Menu
- 1080p Support (And higher if you give me assets!)

## Modes

- **1 Player**: Single player mode. Default
- **2 Player**: Use both keybinds on the entry screen to access
- **Dan Mode**: Access by creating a dan dojo folder and placing dan course jsons in it

## System Requirements

- **Windows**: Windows 10 or higher
- **macOS**: macOS 10.14 (Mojave) or higher
- **Linux**: Ubuntu 20.04 or higher (other distributions may work but are untested)

> **Note**: Operating systems below these requirements are not supported.

## FAQ

Q: I'm on Windows and I have no sound!<br>
A: Change your `device_type` in `config.toml` to `0` (you can experiment with other values which will give better latency)<br>
<br>
Q: I want to add more song paths!<br>
A: You can either append new folders:<br>
`tja_path = ["/run/media/yonokid/HDD/Games/PyTaiko/Songs", "Songs", "Cool Folder"]`<br>
or replace the base one:<br>
`tja_path = ["/run/media/yonokid/HDD/Games/PyTaiko/Songs"]`<br>
Just make sure to use `/` and not `\`!
## Installation

### Pre-built Binaries

Download the latest release for your operating system from the [releases page](https://github.com/Yonokid/PyTaiko/releases).

#### Windows
1. Install the [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) from Microsoft
2. Run `PyTaiko.exe`

#### macOS
- Run with Python directly (see [Building from Source](#building-from-source))

#### Linux
- Try running the compiled `PyTaiko.bin` binary
- If that doesn't work, fall back to running with Python (see [Building from Source](#building-from-source))

#### NixOS

Use the provided `shell.nix` environment:
```nix
{ pkgs ? import <nixpkgs> {} }:
(pkgs.buildFHSEnv {
  name = "PyTaiko-env";
  targetPkgs = pkgs: (with pkgs; [
    python3Full
    gcc
    libGL
    uv
    patchelf
    portaudio
    zlib
    python312Packages.pyaudio
    python312Packages.nuitka
    python312Packages.numpy
    alsa-lib
    xorg.libX11 xorg.libxcb xorg.libXcomposite
    xorg.libXdamage xorg.libXext xorg.libXfixes
    xorg.libXrender xorg.libxshmfence xorg.libXtst
    xorg.libXi
    xorg.xcbutilkeysyms
  ]);
  runScript = "bash";
}).env
```

Then run with Python as described in the Building from Source section.

## Building from Source

### Prerequisites

- [uv](https://docs.astral.sh/uv/) package manager
- Python 3.12+
- Git

### C Libraries
```bash
sudo apt install libsamplerate libsndfile
```

Some distributions may also require [patchelf](https://github.com/NixOS/patchelf) and this symbolic link:
```bash
sudo ln -s /lib/libatomic.so /lib/libatomic.a
```

### Build Steps

1. Clone the repository:
```bash
git clone https://github.com/Yonokid/PyTaiko
cd PyTaiko
```

2. **(Optional)** Compile audio libraries:
```bash
cd libs/audio
make
# Move compiled libraries to main directory
```
You can also reuse the DLLs/libraries from the pre-built releases.
This step is required for MacOS.

3. Run the game:
```bash
uv run PyTaiko.py
```

### Creating Executables

#### Windows/macOS/Linux
```bash
uv add nuitka
uv run nuitka --mode=app --noinclude-setuptools-mode=nofollow --noinclude-IPython-mode=nofollow --assume-yes-for-downloads PyTaiko.py
```

## Controls

- Press **F1** during gameplay for quick restart
- Press **ESC** during any screen to go back
- Generic drum keybinds can be customized in `config.toml` or through the in-game settings menu

## Contributing
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Yonokid/PyTaiko)

Contributions are welcome! Please keep in mind:
- Be mindful of existing built-in functions for animations, videos, and other features. Nearly everything has been abstracted and the libs folder has proper documentation for usage.
- You can also check the [DeepWiki](https://deepwiki.com/Yonokid/PyTaiko) page for a detailed explanation of any code.
- Check the [issues page](https://github.com/Yonokid/PyTaiko/issues) for enhancements and bugs before starting work
- Feel free to open new issues for bugs or feature requests

## Known Issues

See the [issues page](https://github.com/Yonokid/PyTaiko/issues) for current bugs and planned enhancements.

## License

This project is licensed under the terms specified in the LICENSE file.

## Acknowledgments

Built with [raylib](https://www.raylib.com/) - A simple and easy-to-use library to enjoy videogames programming.
More credits coming soon

## Video demo

[![DEMO VIDEO](https://img.youtube.com/vi/b-2pODPl0II/0.jpg)](https://www.youtube.com/watch?v=b-2pODPl0II)

---
