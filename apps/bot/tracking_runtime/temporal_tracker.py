"""Tracking temporal leve entre inferências."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from apps.bot.detector.base import DetectionResult


@dataclass
class TrackedTarget:
    detection: DetectionResult
    timestamp: float
    tracking_confidence: float


class TemporalTracker:
    def __init__(self, timeout_ms: int, ema_alpha: float):
        self._timeout_ms = timeout_ms
        self._ema_alpha = ema_alpha
        self._last: Optional[TrackedTarget] = None

    def update(self, detection: Optional[DetectionResult]) -> Optional[TrackedTarget]:
        now = time.time()
        if detection is not None:
            if self._last is None:
                confidence = detection.confidence
            else:
                confidence = self._ema_alpha * detection.confidence + (1.0 - self._ema_alpha) * self._last.tracking_confidence
            self._last = TrackedTarget(detection=detection, timestamp=now, tracking_confidence=float(confidence))
            return self._last

        if self._last is None:
            return None

        if (now - self._last.timestamp) * 1000.0 > self._timeout_ms:
            self._last = None
            return None
        return self._last
