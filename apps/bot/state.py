"""Estado compartilhado entre threads de captura/tracking/web."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2

from .runtime.settings import RuntimeSettingsStore, VisionRuntimeSettings
from .telemetry.pipeline_metrics import MetricsStore


@dataclass
class RuntimeState:
    mode: str = "auto"
    target_angle: float = 90.0
    servo_enabled: bool = True
    desired_camera_index: int = 0
    active_camera_index: Optional[int] = None
    resolution: str = "0x0"
    latest_frame: Optional[object] = None
    latest_mask: Optional[object] = None
    last_seen_ts: float = 0.0
    vision_running: bool = False
    vision_last_error: Optional[str] = None
    vision_fps: float = 0.0


class SharedState:
    def __init__(self, jpeg_quality: int, show_mask: bool, runtime_settings: RuntimeSettingsStore):
        self._lock = threading.Lock()
        self.jpeg_quality = jpeg_quality
        self.show_mask = show_mask
        self.running = True
        self.runtime = RuntimeState()
        self.runtime_settings = runtime_settings
        self.metrics = MetricsStore()

    def update_visuals(self, frame, mask, resolution: str):
        with self._lock:
            self.runtime.latest_frame = frame
            self.runtime.latest_mask = mask
            self.runtime.resolution = resolution

    def clear_visuals(self, resolution: str = "0x0"):
        with self._lock:
            self.runtime.latest_frame = None
            self.runtime.latest_mask = None
            self.runtime.resolution = resolution

    def mark_seen(self):
        with self._lock:
            self.runtime.last_seen_ts = time.time()

    def set_desired_camera_index(self, camera_index: int):
        with self._lock:
            self.runtime.desired_camera_index = camera_index

    def set_active_camera_index(self, camera_index: Optional[int]):
        with self._lock:
            self.runtime.active_camera_index = camera_index

    def set_vision_running(self, running: bool):
        with self._lock:
            self.runtime.vision_running = running

    def set_vision_error(self, error: Optional[str]):
        with self._lock:
            self.runtime.vision_last_error = error

    def set_vision_fps(self, fps: float):
        with self._lock:
            self.runtime.vision_fps = fps

    def get_runtime_snapshot(self) -> RuntimeState:
        with self._lock:
            return RuntimeState(**self.runtime.__dict__)

    def get_runtime_settings_snapshot(self) -> VisionRuntimeSettings:
        return self.runtime_settings.snapshot()

    def get_jpeg_frame(self):
        with self._lock:
            frame = self.runtime.latest_frame
        if frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
        return buf.tobytes() if ok else None

    def get_jpeg_mask(self):
        if not self.show_mask:
            return None
        with self._lock:
            mask = self.runtime.latest_mask
        if mask is None:
            return None
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        ok, buf = cv2.imencode(".jpg", mask_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
        return buf.tobytes() if ok else None
