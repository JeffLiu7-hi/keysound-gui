from __future__ import annotations

import logging
import sys
from typing import Callable

from .keynames import iter_candidate_names, key_candidates

LOGGER = logging.getLogger(__name__)

Handler = Callable[[str], bool]

if sys.platform == "darwin":
    try:  # pragma: no cover - mac-only import
        from .mac_listener import MacKeyListener
    except Exception as exc:  # pragma: no cover
        MacKeyListener = None  # type: ignore
        LOGGER.warning("Failed to initialise macOS listener: %s", exc)
else:  # pragma: no cover - attribute for type checkers
    MacKeyListener = None  # type: ignore


class _PynputListener:
    def __init__(self, handler: Handler) -> None:
        try:
            from pynput import keyboard
        except ImportError as exc:  # pragma: no cover - dependency missing
            raise ImportError(
                "pynput is required on this platform. Install dependencies with 'pip install -r requirements.txt'."
            ) from exc
        self._keyboard = keyboard
        self._handler = handler
        self._listener: keyboard.Listener | None = None

    def start(self) -> None:
        if self._listener is not None:
            return

        def _on_press(key):
            for candidate in iter_candidate_names(key):
                LOGGER.debug("pynput dispatch %s", candidate)
                if self._handler(candidate):
                    return

        self._listener = self._keyboard.Listener(on_press=_on_press)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        listener = self._listener
        self._listener = None
        try:
            listener.stop()
            listener.join()
        except RuntimeError:
            pass


class _MacListenerWrapper:
    def __init__(self, handler: Handler) -> None:
        if MacKeyListener is None:  # pragma: no cover - defensive
            raise RuntimeError("macOS listener unavailable")
        self._listener = MacKeyListener(self._handle)
        self._handler = handler

    def _handle(self, name: str) -> bool:
        LOGGER.debug("mac listener dispatch %s", name)
        for candidate in key_candidates(name):
            if self._handler(candidate):
                return True
        return False

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()


class GlobalKeyListener:
    def __init__(self, handler: Handler) -> None:
        self._handler = handler
        if sys.platform == "darwin" and MacKeyListener is not None:
            self._impl = _MacListenerWrapper(self._dispatch)
        else:
            self._impl = _PynputListener(self._dispatch)

    def start(self) -> None:
        self._impl.start()

    def stop(self) -> None:
        self._impl.stop()

    def _dispatch(self, name: str) -> bool:
        try:
            return self._handler(name)
        except Exception:  # pragma: no cover
            LOGGER.exception("Key handler failed for name %s", name)
            return False


__all__ = ["GlobalKeyListener"]
