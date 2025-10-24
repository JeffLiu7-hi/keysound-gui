from __future__ import annotations

import json
import logging
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np

from .config import Mode

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioClip:
    samples: np.ndarray  # shape: (frames, channels), dtype float32 in [-1, 1]
    sample_rate: int

    @property
    def channels(self) -> int:
        return int(self.samples.shape[1])

    @property
    def frame_count(self) -> int:
        return int(self.samples.shape[0])

    def to_channels(self, channels: int) -> "AudioClip":
        if channels == self.channels:
            return self
        if self.channels == 1 and channels == 2:
            expanded = np.repeat(self.samples, 2, axis=1)
            return AudioClip(expanded, self.sample_rate)
        if self.channels == 2 and channels == 1:
            collapsed = self.samples.mean(axis=1, keepdims=True)
            return AudioClip(collapsed, self.sample_rate)
        raise ValueError(f"Cannot convert {self.channels} channels clip to {channels}")


class AudioLibrary:
    def __init__(self, mode: Mode, source: Path) -> None:
        self.mode = mode
        self.source = source
        self.sample_rate: Optional[int] = None
        self.channels: Optional[int] = None
        self._clips: Dict[str, AudioClip] = {}
        self.default_clip: Optional[AudioClip] = None
        self._path_cache: Dict[Path, AudioClip] = {}
        self._load()

    @property
    def available_keys(self) -> Iterable[str]:
        return self._clips.keys()

    def clip_for_name(self, name: str) -> Optional[AudioClip]:
        return self._clips.get(name)

    def _load(self) -> None:
        if self.mode is Mode.SINGLE_FILE:
            clip = self._load_clip(self.source)
            clip = self._ensure_format(clip)
            self._clips["default"] = clip
            self.default_clip = clip
        elif self.mode is Mode.DIRECTORY:
            self._load_directory(self.source)
        elif self.mode is Mode.JSON:
            self._load_json(self.source)
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")

        if not self._clips:
            raise ValueError("No audio clips were loaded")
        if self.default_clip is None:
            self.default_clip = self._clips.get("default")
        if self.default_clip is None:
            self.default_clip = next(iter(self._clips.values()))

    def _load_directory(self, directory: Path) -> None:
        if not directory.exists():
            raise FileNotFoundError(f"Audio directory does not exist: {directory}")
        for file in sorted(directory.iterdir()):
            if not file.is_file():
                continue
            if file.suffix.lower() != ".wav":
                continue
            key = file.stem.lower()
            try:
                clip = self._load_clip(file)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to load %s: %s", file, exc)
                continue
            formatted = self._ensure_format(clip)
            self._clips[key] = formatted
            if key == "default":
                self.default_clip = formatted

    def _load_json(self, json_path: Path) -> None:
        with json_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
        if "dir" not in config:
            raise ValueError("JSON configuration must include a 'dir' entry")
        audio_dir = Path(config["dir"])  # type: ignore[arg-type]
        if not audio_dir.is_absolute():
            audio_dir = (json_path.parent / audio_dir).resolve()
        if not audio_dir.is_dir():
            raise FileNotFoundError(f"Configured audio directory does not exist: {audio_dir}")

        cache: Dict[str, AudioClip] = {}
        for key, value in config.items():
            if key == "dir":
                continue
            wav_name = str(value)
            wav_path = (audio_dir / wav_name).resolve()
            if wav_name in cache:
                clip = cache[wav_name]
            else:
                try:
                    clip = self._load_clip(wav_path)
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("Failed to load %s for key %s: %s", wav_path, key, exc)
                    continue
                cache[wav_name] = clip
            formatted = self._ensure_format(clip)
            key_lower = key.lower()
            self._clips[key_lower] = formatted
            if key_lower == "default":
                self.default_clip = formatted

    def _load_clip(self, path: Path) -> AudioClip:
        if path in self._path_cache:
            return self._path_cache[path]
        with wave.open(str(path), "rb") as wav:
            sample_rate = wav.getframerate()
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            frame_count = wav.getnframes()
            raw = wav.readframes(frame_count)
        samples = _decode_samples(raw, sample_width, channels)
        clip = AudioClip(samples, sample_rate)
        self._path_cache[path] = clip
        return clip

    def _ensure_format(self, clip: AudioClip) -> AudioClip:
        if self.sample_rate is None:
            self.sample_rate = clip.sample_rate
        elif clip.sample_rate != self.sample_rate:
            raise ValueError(
                f"Sample rate mismatch: expected {self.sample_rate}, got {clip.sample_rate}"
            )

        if self.channels is None:
            self.channels = clip.channels
        elif clip.channels != self.channels:
            try:
                clip = clip.to_channels(self.channels)
            except ValueError as exc:
                raise ValueError(
                    f"Channel mismatch: expected {self.channels}, got {clip.channels}"
                ) from exc
        return clip


def _decode_samples(raw: bytes, sample_width: int, channels: int) -> np.ndarray:
    if sample_width == 1:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        data = (data - 128.0) / 128.0
    elif sample_width == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        data /= 32768.0
    elif sample_width == 3:
        data = np.frombuffer(raw, dtype=np.uint8)
        frames = data.size // 3
        data = data.reshape(frames, 3).astype(np.int32)
        signed = data[:, 0] | (data[:, 1] << 8) | (data[:, 2] << 16)
        mask = signed & 0x800000
        signed = (signed & 0x7FFFFF) - mask
        data = signed.astype(np.float32) / 8388608.0
    elif sample_width == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32)
        data /= 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")

    if channels not in (1, 2):
        raise ValueError(f"Unsupported channel count: {channels}")
    if data.ndim == 1:
        data = data.reshape(-1, channels)
    else:
        data = data.reshape(-1, channels)
    return np.asarray(data, dtype=np.float32)


__all__ = ["AudioClip", "AudioLibrary"]
