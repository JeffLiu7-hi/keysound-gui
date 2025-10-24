from __future__ import annotations

import logging
import threading

from .audio import AudioLibrary
from .config import KeysoundConfig
from .keyboard import GlobalKeyListener
from .mixer import Mixer
from .player import AudioPlayer

LOGGER = logging.getLogger(__name__)


class KeysoundRunner:
    def __init__(self, config: KeysoundConfig) -> None:
        config.validate()
        self.config = config
        self.library = AudioLibrary(config.mode, config.source)
        if self.library.sample_rate is None or self.library.channels is None:
            raise RuntimeError("Audio library failed to initialise output format")
        self.mixer = Mixer(self.library.sample_rate, self.library.channels)
        self.player = AudioPlayer(self.mixer, config.block_size)
        self.listener = GlobalKeyListener(self._handle_key)
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            LOGGER.info("Starting keysound runner in %s mode", self.config.mode.value)
            LOGGER.debug("Initialising audio output")
            self.player.start()
            LOGGER.debug("Audio output initialised")
            LOGGER.debug("Starting key listener")
            self.listener.start()
            LOGGER.debug("Key listener running")
            self._running = True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            LOGGER.info("Stopping keysound runner")
            LOGGER.debug("Stopping key listener")
            self.listener.stop()
            LOGGER.debug("Stopping audio output")
            self.player.stop()
            self.mixer.reset()
            LOGGER.debug("Playback resources released")
            self._running = False

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _handle_key(self, key_name: str) -> bool:
        LOGGER.debug("Key event: %s", key_name)
        clip = self.library.clip_for_name(key_name)
        if clip is None and key_name == "default":
            clip = self.library.default_clip
        if clip is None:
            LOGGER.debug("No clip mapped for %s", key_name)
            return False
        self.mixer.queue_clip(clip, self.config.volume)
        LOGGER.debug("Queued clip for %s", key_name)
        return True

    def __enter__(self) -> "KeysoundRunner":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


__all__ = ["KeysoundRunner"]
