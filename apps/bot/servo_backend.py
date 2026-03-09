"""Backend de servo desacoplado da lógica de tracking.

No V0 usamos arquivo compartilhado com o daemon C (softPWM).
No futuro este backend pode ser substituído por PCA9685 sem mexer no tracking/web.
"""

from __future__ import annotations

import os
import time

from .utils import clamp


class FileServoBackend:
    def __init__(self, enabled: bool, target_file: str, min_angle: float, max_angle: float, write_interval_ms: int, min_angle_step: float):
        self.enabled = enabled
        self.target_file = target_file
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.write_interval_s = write_interval_ms / 1000.0
        self.min_angle_step = min_angle_step
        self.last_write_ts = 0.0
        self.last_angle = None

    def set_angle(self, angle: float, force: bool = False) -> float:
        angle = clamp(angle, self.min_angle, self.max_angle)
        if not self.enabled:
            self.last_angle = angle
            return angle

        now = time.time()
        if not force and self.last_angle is not None and abs(angle - self.last_angle) < self.min_angle_step:
            return self.last_angle
        if not force and (now - self.last_write_ts) < self.write_interval_s:
            return self.last_angle if self.last_angle is not None else angle

        os.makedirs(os.path.dirname(self.target_file) or ".", exist_ok=True)
        with open(self.target_file, "w", encoding="utf-8") as fp:
            fp.write(f"{angle:.2f}\n")

        self.last_write_ts = now
        self.last_angle = angle
        return angle
