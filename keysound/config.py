from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path


class Mode(enum.Enum):
    SINGLE_FILE = "file"
    DIRECTORY = "directory"
    JSON = "json"

    @classmethod
    def from_flag(cls, flag: str) -> "Mode":
        normalized = flag.lower()
        if normalized in {"f", "file"}:
            return cls.SINGLE_FILE
        if normalized in {"d", "dir", "directory"}:
            return cls.DIRECTORY
        if normalized in {"j", "json"}:
            return cls.JSON
        raise ValueError(f"Unsupported mode flag: {flag}")


@dataclass(frozen=True)
class KeysoundConfig:
    mode: Mode
    source: Path
    block_size: int = 1024
    volume: float = 1.0

    def validate(self) -> None:
        if self.block_size <= 0:
            raise ValueError("block_size must be positive")
        if not 0 < self.volume <= 4.0:
            raise ValueError("volume must be between 0 and 4")
        if self.mode in {Mode.SINGLE_FILE, Mode.JSON}:
            if not self.source.is_file():
                raise FileNotFoundError(f"Expected file for mode {self.mode.value}: {self.source}")
        elif self.mode is Mode.DIRECTORY and not self.source.is_dir():
            raise FileNotFoundError(f"Expected directory for mode {self.mode.value}: {self.source}")


__all__ = ["Mode", "KeysoundConfig"]
