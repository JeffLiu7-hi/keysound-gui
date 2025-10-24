from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover - dependency resolution validation
    raise ImportError(
        "sounddevice is required. Install dependencies with 'pip install -r requirements.txt'."
    ) from exc

from .mixer import Mixer

LOGGER = logging.getLogger(__name__)


class AudioPlayer:
    def __init__(self, mixer: Mixer, block_size: int):
        self._mixer = mixer
        self._block_size = block_size
        self._stream: Optional[sd.OutputStream] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._stream = sd.OutputStream(
                samplerate=self._mixer.sample_rate,
                blocksize=self._block_size,
                channels=self._mixer.channels,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> None:
        with self._lock:
            if self._stream is None:
                return
            stream = self._stream
            self._stream = None
        try:
            stream.stop()
        finally:
            stream.close()

    def _callback(self, outdata, frames, time, status) -> None:  # pragma: no cover - realtime
        if status:
            LOGGER.warning("Audio callback status: %s", status)
        block = self._mixer.mix(frames)
        if block.shape[0] < frames:
            padded = np.zeros((frames, self._mixer.channels), dtype="float32")
            padded[: block.shape[0]] = block
            outdata[:] = padded
        else:
            outdata[:] = block


__all__ = ["AudioPlayer"]
