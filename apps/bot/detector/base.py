"""Interfaces e modelos de dados para detectores de segmentação."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol, Sequence, Tuple

import numpy as np


@dataclass
class DetectionResult:
    """Resultado normalizado de uma detecção com segmentação por instância."""

    class_name: str
    class_id: int
    confidence: float
    bounding_box: Tuple[int, int, int, int]
    segmentation_mask: np.ndarray
    contour_polygon: List[Tuple[int, int]]
    centroid: Tuple[int, int]
    visible_area: float


@dataclass
class DetectorFrameOutput:
    """Saída de inferência para um frame."""

    detections: Sequence[DetectionResult]
    inference_ms: float


class SegmentationDetector(Protocol):
    """Contrato para detectores com máscara de segmentação."""

    @property
    def classes(self) -> List[str]:
        ...

    def infer(self, frame: np.ndarray, target_classes: Optional[Sequence[int]] = None) -> DetectorFrameOutput:
        ...
