"""Integração oficial Ultralytics para YOLO nano segmentation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

import cv2
import numpy as np

from .base import DetectionResult, DetectorFrameOutput, SegmentationDetector


@dataclass
class YoloSegConfig:
    model_path: str = "yolo26n-seg.pt"
    conf_threshold: float = 0.25
    iou_threshold: float = 0.45
    imgsz: int = 640
    retina_masks: bool = True
    device: Optional[str] = None


class YoloNanoSegDetector(SegmentationDetector):
    """Detector segmentador padronizado em YOLO nano da stack Ultralytics."""

    def __init__(self, config: YoloSegConfig):
        self._config = config
        try:
            from ultralytics import YOLO
        except Exception as exc:  # pragma: no cover - depende de runtime real
            raise RuntimeError("Pacote ultralytics indisponível para detector YOLO nano segmentation") from exc

        self._model = YOLO(config.model_path)
        self._names = self._extract_names(self._model.names)

    @staticmethod
    def _extract_names(raw_names) -> List[str]:
        if isinstance(raw_names, dict):
            return [raw_names[idx] for idx in sorted(raw_names.keys())]
        if isinstance(raw_names, list):
            return raw_names
        return []

    @property
    def classes(self) -> List[str]:
        return self._names

    def infer(self, frame: np.ndarray, target_classes: Optional[Sequence[int]] = None) -> DetectorFrameOutput:
        start = time.perf_counter()
        results = self._model.predict(
            source=frame,
            task="segment",
            conf=self._config.conf_threshold,
            iou=self._config.iou_threshold,
            imgsz=self._config.imgsz,
            retina_masks=self._config.retina_masks,
            classes=list(target_classes) if target_classes else None,
            device=self._config.device,
            verbose=False,
        )
        inference_ms = (time.perf_counter() - start) * 1000.0
        detections = self._parse_results(results, frame.shape[:2])
        return DetectorFrameOutput(detections=detections, inference_ms=inference_ms)

    def _parse_results(self, results, frame_shape) -> List[DetectionResult]:
        height, width = frame_shape
        parsed: List[DetectionResult] = []

        for result in results:
            if result.boxes is None or result.masks is None:
                continue

            boxes_xyxy = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            class_ids = result.boxes.cls.cpu().numpy().astype(int)
            masks_data = result.masks.data.cpu().numpy()

            for idx, mask_data in enumerate(masks_data):
                mask_u8 = (mask_data > 0.5).astype(np.uint8) * 255
                if mask_u8.shape != (height, width):
                    mask_u8 = cv2.resize(mask_u8, (width, height), interpolation=cv2.INTER_NEAREST)

                contour = self._largest_contour(mask_u8)
                centroid = self._compute_centroid(mask_u8, contour)
                x1, y1, x2, y2 = boxes_xyxy[idx]
                class_id = int(class_ids[idx])
                class_name = self._names[class_id] if 0 <= class_id < len(self._names) else f"class_{class_id}"

                parsed.append(
                    DetectionResult(
                        class_name=class_name,
                        class_id=class_id,
                        confidence=float(confidences[idx]),
                        bounding_box=(int(x1), int(y1), int(x2), int(y2)),
                        segmentation_mask=mask_u8,
                        contour_polygon=contour,
                        centroid=centroid,
                        visible_area=float(np.count_nonzero(mask_u8)),
                    )
                )
        return parsed

    @staticmethod
    def _largest_contour(mask: np.ndarray) -> List[tuple[int, int]]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []
        contour = max(contours, key=cv2.contourArea)
        return [(int(point[0][0]), int(point[0][1])) for point in contour]

    @staticmethod
    def _compute_centroid(mask: np.ndarray, contour_polygon: List[tuple[int, int]]) -> tuple[int, int]:
        if contour_polygon:
            contour_np = np.array(contour_polygon, dtype=np.int32).reshape((-1, 1, 2))
            moments = cv2.moments(contour_np)
            if moments["m00"]:
                return int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"])

        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            return 0, 0
        return int(xs.mean()), int(ys.mean())
