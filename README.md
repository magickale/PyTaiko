
# PyTaiko

This is a TJA player / Taiko simulator written in python and uses the [raylib](https://www.raylib.com/) library.


## Installation

Windows 10, Mac OS X 10.14 and Ubuntu 20.04 and higher are supported.
Any operating system below these requirements will not work.
Any Linux distro not listed is up to your own discretion
Download for OS of choice on releases page

How to run:
Windows:
```
  Run PyTaiko.exe
```
MacOS:
```
Good luck, would suggest running with python directly
```
Linux:
```
    Run PyTaiko.bin for Debian based systems, otherwise run python
```
Nix OS:
Use the provided shell.nix code and run with python:
```
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

## Roadmap

See "enhancements" on issues page


## Known Issues

See "bugs" on issues page


## Run Locally

If not installed, install [uv](https://docs.astral.sh/uv/)

Clone the project

```bash
  git clone https://github.com/Yonokid/PyTaiko
```

Go to the project directory

```bash
  cd PyTaiko
````

Start the game

```bash
  uv run PyTaiko.py
```

## Compilation
Windows/Mac OS:
```
uv add nuitka
uv run nuitka --mode=app --noinclude-setuptools-mode=nofollow --noinclude-IPython-mode=nofollow --assume-yes-for-downloads PyTaiko.py
```
Linux:
Install portaudio with `sudo apt install portaudio19-dev`

Some Linux distributions may need this:
Install [patchelf](https://github.com/NixOS/patchelf)
Run this command
```
sudo ln -s /lib/libatomic.so /lib/libatomic.a
```

## FAQ

#### Keybinds?

Hit F1 in entry screen to access settings menu
Hit F1 in game to quick restart

#### Why does it look like Gen 3 instead of Nijiiro?

I like it


## Contributing

Contributions are now open. I don't have any particular contribution guidelines other than be mindful of what builtin functions already exist in this project (ie, for animations, videos, etc)
