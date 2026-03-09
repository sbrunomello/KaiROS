"""Renderização de overlay de máscara, contorno e labels."""

from __future__ import annotations

import cv2
import numpy as np

from apps.bot.detector.base import DetectionResult


def draw_detection_overlay(
    frame: np.ndarray,
    detection: DetectionResult,
    *,
    draw_mask: bool,
    draw_bbox: bool,
    draw_contour: bool,
    draw_label: bool,
    overlay_alpha: float,
) -> np.ndarray:
    output = frame.copy()

    if draw_mask:
        color_layer = np.zeros_like(output)
        color_layer[detection.segmentation_mask > 0] = (64, 200, 32)
        output = cv2.addWeighted(color_layer, overlay_alpha, output, 1 - overlay_alpha, 0)

    if draw_contour and detection.contour_polygon:
        points = np.array(detection.contour_polygon, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(output, [points], isClosed=True, color=(0, 255, 255), thickness=2)

    if draw_bbox:
        x1, y1, x2, y2 = detection.bounding_box
        cv2.rectangle(output, (x1, y1), (x2, y2), (255, 150, 0), 2)

    cx, cy = detection.centroid
    cv2.circle(output, (cx, cy), 4, (255, 255, 255), -1)

    if draw_label:
        label = f"{detection.class_name} {detection.confidence:.2f}"
        anchor = (max(0, cx - 40), max(18, cy - 10))
        cv2.putText(output, label, anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 255, 20), 2)

    return output
