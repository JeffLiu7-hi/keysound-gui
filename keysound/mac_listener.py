from __future__ import annotations

import logging
import sys
import threading
from typing import Callable

from .mac_keys import keycode_to_name

LOGGER = logging.getLogger(__name__)

Handler = Callable[[str], bool]


def _check_accessibility_permission() -> bool:
    """Return True when macOS Accessibility permission is granted."""
    try:
        from Quartz import (  # type: ignore
            AXIsProcessTrusted,
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
    except Exception as exc:  # pragma: no cover - PyObjC not available
        LOGGER.debug("Quartz accessibility check unavailable via PyObjC: %s", exc)
        try:
            import ctypes
            from ctypes import util

            path = util.find_library("ApplicationServices")
            if not path:
                LOGGER.warning("Unable to locate ApplicationServices framework to verify accessibility permission")
                return True
            quartz = ctypes.cdll.LoadLibrary(path)
            quartz.AXIsProcessTrusted.restype = ctypes.c_bool
            quartz.AXIsProcessTrusted.argtypes = []
            return bool(quartz.AXIsProcessTrusted())
        except Exception as cexc:  # pragma: no cover
            LOGGER.warning("Unable to verify accessibility permission: %s", cexc)
            return True

    try:
        trusted = AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except TypeError:  # pragma: no cover - macOS < 10.9 fallback
        trusted = AXIsProcessTrusted()
    return bool(trusted)


def _ensure_macos_accessibility() -> None:
    if not _check_accessibility_permission():
        raise PermissionError(
            "macOS Accessibility permission required. Enable it in System Settings → Privacy & Security → Accessibility for the python executable running keysound."
        )


class MacKeyListener:
    def __init__(self, handler: Handler) -> None:
        if sys.platform != "darwin":  # pragma: no cover - defensive
            raise RuntimeError("MacKeyListener is only available on macOS")
        self._handler = handler
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._run_loop = None
        self._tap = None

    def start(self) -> None:
        if self._thread is not None:
            return
        _ensure_macos_accessibility()
        self._stop_event.clear()
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._run, name="KeysoundMacKeyListener", daemon=True)
        self._thread.start()
        if not self._ready_event.wait(timeout=5):
            self._thread = None
            raise RuntimeError("Failed to start macOS key listener")

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        try:
            from Quartz import CFRunLoopStop  # type: ignore
        except Exception:
            CFRunLoopStop = None  # type: ignore
        if CFRunLoopStop and self._run_loop is not None:
            CFRunLoopStop(self._run_loop)
        self._thread.join(timeout=1.0)
        self._thread = None
        self._run_loop = None
        self._tap = None

    def _run(self) -> None:
        try:
            from Quartz import (  # type: ignore
                CFMachPortCreateRunLoopSource,
                CFMachPortInvalidate,
                CFRunLoopAddSource,
                CFRunLoopGetCurrent,
                CFRunLoopRemoveSource,
                CFRunLoopRunInMode,
                CGEventGetIntegerValueField,
                CGEventMaskBit,
                CGEventTapCreate,
                CGEventTapEnable,
                kCFRunLoopDefaultMode,
                kCGEventKeyDown,
                kCGEventTapDisabledByTimeout,
                kCGHIDEventTap,
                kCGHeadInsertEventTap,
                kCGKeyboardEventKeycode,
            )
        except Exception as exc:  # pragma: no cover - dependency failure
            LOGGER.error("Quartz APIs unavailable: %s", exc)
            self._ready_event.set()
            return

        def _callback(proxy, event_type, event, refcon):  # pragma: no cover - executed by CoreGraphics
            if event_type == kCGEventTapDisabledByTimeout and self._tap is not None:
                CGEventTapEnable(self._tap, True)
                return event
            if event_type != kCGEventKeyDown:
                return event
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            name = keycode_to_name(int(keycode))
            LOGGER.debug("mac keydown keycode=%s name=%s", keycode, name)
            try:
                self._handler(name)
            except Exception:
                LOGGER.exception("Mac key handler failed for keycode %s", keycode)
            return event

        event_mask = CGEventMaskBit(kCGEventKeyDown)
        tap = CGEventTapCreate(
            kCGHIDEventTap,
            kCGHeadInsertEventTap,
            0,
            event_mask,
            _callback,
            None,
        )

        if not tap:
            LOGGER.error("Unable to create event tap")
            self._ready_event.set()
            return

        run_loop = CFRunLoopGetCurrent()
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        CFRunLoopAddSource(run_loop, source, kCFRunLoopDefaultMode)
        CGEventTapEnable(tap, True)

        self._tap = tap
        self._run_loop = run_loop
        self._ready_event.set()

        try:
            while not self._stop_event.is_set():
                CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, True)
        finally:
            CFRunLoopRemoveSource(run_loop, source, kCFRunLoopDefaultMode)
            CFMachPortInvalidate(tap)


__all__ = ["MacKeyListener"]
