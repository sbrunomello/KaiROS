"""Configuração de visão e estado runtime mutável pelo frontend."""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class VisionRuntimeSettings:
    target_class: str = "all"
    infer_every_n_frames: int = 1
    draw_bbox: bool = False
    draw_mask: bool = True
    draw_contour: bool = True
    draw_label: bool = True
    retina_masks: bool = True
    conf_threshold: float = 0.25


class RuntimeSettingsStore:
    def __init__(self, defaults: VisionRuntimeSettings):
        self._lock = threading.Lock()
        self._settings = defaults

    def snapshot(self) -> VisionRuntimeSettings:
        with self._lock:
            return VisionRuntimeSettings(**asdict(self._settings))

    def update(self, **kwargs: Any) -> VisionRuntimeSettings:
        with self._lock:
            for key, value in kwargs.items():
                if value is None or not hasattr(self._settings, key):
                    continue
                setattr(self._settings, key, value)
            if self._settings.infer_every_n_frames < 1:
                self._settings.infer_every_n_frames = 1
            return VisionRuntimeSettings(**asdict(self._settings))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self.snapshot())
