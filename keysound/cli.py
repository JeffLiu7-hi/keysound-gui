from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .config import KeysoundConfig, Mode
from .runner import KeysoundRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Global key sound playback in Python")
    parser.add_argument("--file", "-f", type=Path, help="Single WAV file to use for all keys")
    parser.add_argument("--dir", "-d", type=Path, help="Directory with per-key WAV files")
    parser.add_argument("--json", "-j", type=Path, help="JSON configuration mapping keys to audio files")
    parser.add_argument("--block-size", type=int, default=1024, help="Audio callback block size")
    parser.add_argument("--volume", type=float, default=1.0, help="Playback volume multiplier")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface")
    parser.add_argument("--list-keys", action="store_true", help="List the keys with configured audio and exit")
    parser.add_argument("--log-level", default="WARNING", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    return parser


def choose_mode(args: argparse.Namespace) -> tuple[Mode, Path]:
    choices = [(Mode.SINGLE_FILE, args.file), (Mode.DIRECTORY, args.dir), (Mode.JSON, args.json)]
    provided = [(mode, path) for mode, path in choices if path is not None]
    if len(provided) > 1:
        raise ValueError("Please specify only one of --file, --dir or --json")
    if not provided:
        raise ValueError("Specify one of --file, --dir or --json, or use --gui")
    mode, path = provided[0]
    return mode, Path(path).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO),
                        format="[%(levelname)s] %(message)s")

    if args.gui:
        from .gui import run as run_gui

        run_gui()
        return 0

    try:
        mode, source = choose_mode(args)
    except ValueError as exc:
        parser.error(str(exc))

    config = KeysoundConfig(mode=mode, source=source,
                            block_size=args.block_size, volume=args.volume)

    runner = KeysoundRunner(config)

    if args.list_keys:
        for key in sorted(runner.library.available_keys):
            print(key)
        return 0

    try:
        runner.start()
    except PermissionError as exc:
        print(f"Error: {exc}")
        return 1

    print("Keysound running. Press Ctrl+C to stop.")

    try:
        while runner.is_running():
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        runner.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
