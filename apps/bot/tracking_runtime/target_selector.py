"""Seleção de alvo com filtro por classe em tempo real."""

from __future__ import annotations

from typing import Iterable, Optional

from apps.bot.detector.base import DetectionResult


class TargetSelector:
    """Seleciona alvo com base na classe alvo e na confiança."""

    def pick(self, detections: Iterable[DetectionResult], target_class: Optional[str]) -> Optional[DetectionResult]:
        if target_class and target_class != "all":
            filtered = [det for det in detections if det.class_name == target_class]
        else:
            filtered = list(detections)
        if not filtered:
            return None
        return max(filtered, key=lambda det: det.confidence)
