"""Métricas de pipeline em tempo real com agregados úteis."""

from __future__ import annotations

import statistics
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Deque, Dict, Optional


@dataclass
class PipelineMetrics:
    frame_fps: float = 0.0
    inference_fps: float = 0.0
    inference_ms: float = 0.0
    capture_ms: float = 0.0
    preprocess_ms: float = 0.0
    render_ms: float = 0.0
    target_found: bool = False
    class_name: Optional[str] = None
    class_confidence: float = 0.0
    tracking_confidence: float = 0.0
    mask_area: float = 0.0
    centroid_x: int = 0
    centroid_y: int = 0
    infer_every_n_frames: int = 1
    current_target_class: str = "all"
    dropped_inference_count: int = 0
    last_valid_detection_ts: float = 0.0


class MetricsStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._metrics = PipelineMetrics()
        self._inference_history: Deque[float] = deque(maxlen=120)

    def update(self, **kwargs: Any) -> PipelineMetrics:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._metrics, key):
                    setattr(self._metrics, key, value)
            inference_ms = kwargs.get("inference_ms")
            if isinstance(inference_ms, (int, float)) and inference_ms > 0:
                self._inference_history.append(float(inference_ms))
            return PipelineMetrics(**asdict(self._metrics))

    def mark_detection_found(self):
        self.update(last_valid_detection_ts=time.time(), target_found=True)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            payload = asdict(self._metrics)
            samples = list(self._inference_history)

        if samples:
            payload["inference_avg_ms"] = float(sum(samples) / len(samples))
            payload["inference_p50_ms"] = float(statistics.median(samples))
            payload["inference_p95_ms"] = float(sorted(samples)[int(0.95 * (len(samples) - 1))])
        else:
            payload["inference_avg_ms"] = 0.0
            payload["inference_p50_ms"] = 0.0
            payload["inference_p95_ms"] = 0.0
        return payload
