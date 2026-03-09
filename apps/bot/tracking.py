"""Lógica de tracking HSV baseada na POC validada em hardware."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from .utils import clamp

HSVRange = Tuple[Tuple[int, int, int], Tuple[int, int, int]]

COLOR_PRESETS: Dict[str, List[HSVRange]] = {
    "blue": [((100, 120, 70), (130, 255, 255))],
    "green": [((35, 80, 60), (85, 255, 255))],
    "yellow": [((20, 100, 100), (35, 255, 255))],
    "red": [
        ((0, 120, 70), (10, 255, 255)),
        ((170, 120, 70), (179, 255, 255)),
    ],
}


def build_mask(hsv: np.ndarray, color_name: str) -> np.ndarray:
    """Cria máscara HSV com open+close para reduzir ruído."""
    combined = None
    for lower, upper in COLOR_PRESETS[color_name]:
        part = cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
        combined = part if combined is None else cv2.bitwise_or(combined, part)

    kernel = np.ones((5, 5), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
    return combined


def detect_largest_blob(mask: np.ndarray, area_min: int) -> Optional[Tuple[int, int, int, int, float]]:
    """Retorna bounding box e área do maior contorno válido."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < area_min:
        return None

    x, y, w, h = cv2.boundingRect(contour)
    return x, y, w, h, float(area)


def compute_error_norm(target_x: int, frame_width: int) -> float:
    center_x = max(1, frame_width // 2)
    return (target_x - center_x) / center_x


def compute_target_angle(current: float, error_norm: float, kp: float, deadband: float, min_angle: float, max_angle: float) -> float:
    if abs(error_norm) <= deadband:
        return current
    return clamp(current + kp * error_norm, min_angle, max_angle)
