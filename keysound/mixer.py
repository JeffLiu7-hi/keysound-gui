from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

from .audio import AudioClip


@dataclass
class PlaybackInstance:
    clip: AudioClip
    volume: float
    position: int = 0


class Mixer:
    def __init__(self, sample_rate: int, channels: int) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._lock = threading.Lock()
        self._instances: list[PlaybackInstance] = []

    def queue_clip(self, clip: AudioClip, volume: float) -> None:
        instance = PlaybackInstance(clip=clip, volume=volume)
        with self._lock:
            self._instances.append(instance)
        # Debug-level logging happens elsewhere to avoid import cycle

    def mix(self, frames: int) -> np.ndarray:
        block = np.zeros((frames, self.channels), dtype=np.float32)
        finished: list[PlaybackInstance] = []
        with self._lock:
            for instance in self._instances:
                clip_frames = instance.clip.frame_count
                remaining = clip_frames - instance.position
                if remaining <= 0:
                    finished.append(instance)
                    continue
                take = min(frames, remaining)
                chunk = instance.clip.samples[instance.position : instance.position + take]
                if chunk.shape[1] != self.channels:
                    # Safety guard; should not happen
                    if chunk.shape[1] == 1 and self.channels == 2:
                        chunk = np.repeat(chunk, 2, axis=1)
                    elif chunk.shape[1] > self.channels:
                        chunk = chunk[:, : self.channels]
                    else:
                        chunk = np.pad(chunk, ((0, 0), (0, self.channels - chunk.shape[1])), mode="edge")
                block[:take] += chunk * instance.volume
                instance.position += take
                if instance.position >= clip_frames:
                    finished.append(instance)
            if finished:
                self._instances = [i for i in self._instances if i not in finished]
        np.clip(block, -1.0, 1.0, out=block)
        return block

    def reset(self) -> None:
        with self._lock:
            self._instances.clear()


__all__ = ["Mixer", "PlaybackInstance"]
