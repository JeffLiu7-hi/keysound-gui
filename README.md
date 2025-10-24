# Keysound (Python Edition)

A cross-platform keyboard sound utility implemented in Python. Keysound listens for global key presses and plays configurable audio clips so you can attach typewriter, piano, or any custom sounds to your keyboard on Linux, Windows, or macOS.

## Highlights

- Works on Linux, Windows, and macOS using `pynput` for global key detection.
- Flexible audio routing: use one WAV for every key, provide a directory of per-key clips, or describe mappings with JSON.
- Real-time mixing with `sounddevice`, so overlapping key presses blend smoothly.
- Lightweight Tk GUI for configuring sources without editing the command line.
- Backwards-compatible directory and JSON naming so existing sound packs continue to work.

## Prerequisites

- Python 3.10 or newer.
- System audio stack compatible with PortAudio (already available on most desktops). On Linux you might need `sudo apt install libportaudio2` or the equivalent package.
- macOS only: `pyobjc-framework-Quartz` (installed automatically via `requirements.txt`) and Accessibility/Input Monitoring permissions for the Python interpreter.

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

> **macOS:** after installing the dependencies, open *System Settings → Privacy & Security → Accessibility* (and *Input Monitoring*) and allow the Python executable you use to run Keysound. macOS might prompt the first time you launch the program; if it doesn't, add it manually.

## Quick Start

Run the GUI:

```bash
python -m keysound --gui
```

Command line examples:

```bash
# Use a single WAV for every key
python -m keysound --file audio/typewriter-key.wav

# Use per-key WAV files inside a directory
python -m keysound --dir audio/piano

# Use JSON mapping to point individual keys to files inside "dir"
python -m keysound --json audio/piano.json
```

Press `Ctrl+C` in the terminal to stop the CLI runner. The GUI has explicit Start/Stop buttons.

### Block Size & Volume

Two optional flags control playback characteristics:

- `--block-size` (default `1024`): audio callback buffer size, lower numbers reduce latency.
- `--volume` (default `1.0`): overall gain multiplier, values above `1.0` boost the output.

## Configuration Formats

### Single File

Provide one WAV file with `--file`. That sound plays for every key.

### Directory Mode

Place WAV files in a directory, name files after the keys (case-insensitive, without extension). Examples: `a.wav`, `space.wav`, `enter.wav`, `lshift.wav`. A special `default.wav` handles keys without an explicit entry.

### JSON Mode

A JSON file names an `"dir"` containing the audio clips and maps key strings to filenames. Example:

```json
{
  "dir": "./audio/piano",
  "default": "typewriter-key.wav",
  "a": "40-E.wav",
  "shift": "shift.wav",
  "enter": "enter.wav"
}
```

The directory path can be relative to the JSON file location.

### Key Names

Keys use lowercase strings. Letters use the character itself (`a`, `b`, `c`). Special keys follow `pynput` naming (`space`, `enter`, `tab`, `shift`, `ctrl`, `alt`, `meta`, `up`, `down`, `left`, `right`, etc.). For compatibility, aliases like `lshift`, `rshift`, `lctrl`, `rctrl`, `capslock`, `pagedown`, `pageup`, `home`, `end`, and function keys (`f1` … `f12`) are supported. Anything unresolved falls back to `default` if provided.

You can list the keys recognised in your configuration without starting playback:

```bash
python -m keysound --dir audio/piano --list-keys
```

## GUI Walkthrough

1. Choose between *Single WAV*, *Directory*, or *JSON Config*.
2. Browse to the appropriate file or folder.
3. Optional: tweak block size and volume.
4. Press **Start** and begin typing.
5. Use **Stop** or close the window to end playback.

## Developing

- The core package lives under `keysound/`.
- Run `python -m keysound --file <wav>` during development to exercise the CLI runner.
- The mixer relies on NumPy/SoundDevice; when contributing across platforms, test both keyboard capture and audio output.

## License

MIT
