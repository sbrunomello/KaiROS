import numpy as np

from apps.bot.detector.base import DetectionResult
from apps.bot.detector.yolo_nano_seg import YoloNanoSegDetector
from apps.bot.render.mask_overlay import draw_detection_overlay
from apps.bot.telemetry.pipeline_metrics import MetricsStore
from apps.bot.tracking_runtime.target_selector import TargetSelector
from apps.bot.tracking_runtime.temporal_tracker import TemporalTracker


def test_compute_centroid_from_mask():
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[5:10, 8:12] = 255
    centroid = YoloNanoSegDetector._compute_centroid(mask, [])
    assert centroid[0] in range(8, 12)
    assert centroid[1] in range(5, 10)


def test_target_selector_by_class():
    detection_person = DetectionResult("person", 0, 0.8, (0, 0, 10, 10), np.ones((4, 4), dtype=np.uint8), [], (1, 1), 16)
    detection_car = DetectionResult("car", 1, 0.9, (0, 0, 10, 10), np.ones((4, 4), dtype=np.uint8), [], (1, 1), 16)
    selected = TargetSelector().pick([detection_person, detection_car], "person")
    assert selected.class_name == "person"


def test_overlay_renders_mask_and_label():
    frame = np.zeros((40, 40, 3), dtype=np.uint8)
    mask = np.zeros((40, 40), dtype=np.uint8)
    mask[10:20, 10:20] = 255
    detection = DetectionResult("person", 0, 0.7, (10, 10, 20, 20), mask, [(10, 10), (20, 10), (20, 20), (10, 20)], (15, 15), 100)
    out = draw_detection_overlay(frame, detection, draw_mask=True, draw_bbox=False, draw_contour=True, draw_label=True, overlay_alpha=0.5)
    assert int(out.sum()) > 0


def test_temporal_tracker_keeps_last_target():
    detection = DetectionResult("person", 0, 0.8, (0, 0, 10, 10), np.ones((4, 4), dtype=np.uint8), [], (1, 1), 16)
    tracker = TemporalTracker(timeout_ms=5000, ema_alpha=0.5)
    tracker.update(detection)
    kept = tracker.update(None)
    assert kept is not None


def test_metrics_store_snapshot_contains_aggregates():
    store = MetricsStore()
    store.update(inference_ms=10.0, frame_fps=20.0)
    snap = store.snapshot()
    assert snap["inference_avg_ms"] > 0
    assert "inference_p95_ms" in snap
