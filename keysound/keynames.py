from __future__ import annotations

from typing import Iterable, List

from pynput import keyboard


def _build_special_names() -> dict[keyboard.Key, str]:
    result: dict[keyboard.Key, str] = {}

    def add(attr: str, label: str) -> None:
        key = getattr(keyboard.Key, attr, None)
        if key is not None:
            result[key] = label

    add("space", "space")
    add("enter", "enter")
    add("tab", "tab")
    add("esc", "esc")
    add("backspace", "backspace")
    add("delete", "delete")
    add("insert", "insert")
    add("shift", "shift")
    add("shift_r", "shift_r")
    add("ctrl", "ctrl")
    add("ctrl_r", "ctrl_r")
    add("alt", "alt")
    add("alt_r", "alt_r")
    add("cmd", "meta")
    add("cmd_r", "meta_r")
    add("caps_lock", "capslock")

    for index in range(1, 13):
        add(f"f{index}", f"f{index}")

    add("up", "up")
    add("down", "down")
    add("left", "left")
    add("right", "right")
    add("home", "home")
    add("end", "end")
    add("page_up", "pageup")
    add("page_down", "pagedown")
    add("media_play_pause", "playpause")
    add("media_volume_up", "volumeup")
    add("media_volume_down", "volumedown")
    add("media_next", "nextsong")
    add("media_previous", "previoussong")

    return result


_SPECIAL_NAMES = _build_special_names()

_KEY_ALIASES = {
    "shift": ["lshift", "rshift"],
    "shift_r": ["rshift", "shift"],
    "ctrl": ["lctrl", "control"],
    "ctrl_r": ["rctrl", "control"],
    "alt": ["lalt"],
    "alt_r": ["ralt"],
    "meta": ["lmeta", "super"],
    "meta_r": ["rmeta", "super"],
    "enter": ["return"],
    "capslock": ["caps_lock"],
    "backspace": ["delete", "del"],
    "pagedown": ["page_down"],
    "pageup": ["page_up"],
}


def key_to_name(key: keyboard.Key | keyboard.KeyCode | None) -> str | None:
    if key is None:
        return None
    if isinstance(key, keyboard.KeyCode):
        if key.char:
            return key.char.lower()
        if key.vk is not None:
            return f"vk_{key.vk}"
        return None
    name = _SPECIAL_NAMES.get(key)
    if name:
        return name
    if hasattr(key, "name") and key.name:
        return str(key.name).lower().replace(" ", "_")
    return None


def key_candidates(name: str) -> List[str]:
    base = name.lower()
    candidates: List[str] = [base]
    aliases = _KEY_ALIASES.get(base, [])
    candidates.extend(aliases)
    if len(base) == 1 and base.isalpha():
        candidates.append(base.upper())
    if base == "shift":
        candidates.append("lshift")
        candidates.append("rshift")
    if base == "ctrl":
        candidates.extend(["control", "lctrl", "rctrl"])
    candidates.append("default")
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: List[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def iter_candidate_names(key: keyboard.Key | keyboard.KeyCode | None) -> Iterable[str]:
    name = key_to_name(key)
    if not name:
        yield "default"
        return
    for candidate in key_candidates(name):
        yield candidate


__all__ = ["key_to_name", "key_candidates", "iter_candidate_names"]
