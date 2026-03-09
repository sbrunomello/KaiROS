"""Serviço isolado de visão com YOLO nano segmentation + tracking temporal."""

from __future__ import annotations

import time
from typing import Optional

import cv2

from .detector.yolo_nano_seg import YoloNanoSegDetector, YoloSegConfig
from .render.mask_overlay import draw_detection_overlay
from .tracking_runtime.target_selector import TargetSelector
from .tracking_runtime.temporal_tracker import TemporalTracker

REOPEN_WAIT_SECONDS = 0.3
READ_FAIL_REOPEN_THRESHOLD = 20


class VisionService:
    """Executa captura, inferência de segmentação e atualização de métricas."""

    def __init__(self, cfg: dict, state, servo_service, detector: Optional[YoloNanoSegDetector] = None):
        self._cfg = cfg
        self._state = state
        self._servo_service = servo_service
        detector_cfg = cfg["detector"]
        self._detector = detector or YoloNanoSegDetector(
            YoloSegConfig(
                model_path=detector_cfg["model_path"],
                conf_threshold=detector_cfg["conf_threshold"],
                iou_threshold=detector_cfg["iou_threshold"],
                imgsz=detector_cfg["imgsz"],
                retina_masks=detector_cfg["retina_masks"],
                device=detector_cfg.get("device"),
            )
        )
        self._selector = TargetSelector()
        self._tracker = TemporalTracker(
            timeout_ms=cfg["tracking"]["tracking_timeout_ms"],
            ema_alpha=cfg["tracking"]["ema_alpha"],
        )
        self._frame_count = 0
        self._inference_count = 0

    @property
    def model_classes(self):
        return self._detector.classes

    def _open_camera(self, camera_cfg: dict, camera_index: int):
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_cfg["width"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_cfg["height"])
        cap.set(cv2.CAP_PROP_FPS, camera_cfg["fps"])
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            cap.release()
            return None
        return cap

    def run(self):
        camera_cfg = self._cfg["camera"]
        servo_cfg = self._cfg["servo"]

        self._state.set_active_camera_index(None)
        self._state.set_vision_running(True)
        self._state.set_vision_error(None)
        desired_camera_index = self._state.get_runtime_snapshot().desired_camera_index

        cap = self._open_camera(camera_cfg, desired_camera_index)
        if cap is None:
            self._state.set_vision_running(False)
            self._state.set_vision_error(f"camera_open_failed:{desired_camera_index}")
            raise RuntimeError(f"Não consegui abrir câmera index={desired_camera_index}")

        self._state.set_active_camera_index(desired_camera_index)
        self._state.runtime.target_angle = self._servo_service.center(servo_cfg["center_angle"])
        read_fail_count = 0
        fps_window_start = time.time()
        fps_window_frames = 0
        service_start_ts = time.time()

        while self._state.running:
            capture_start = time.perf_counter()
            runtime = self._state.get_runtime_snapshot()

            if runtime.desired_camera_index != runtime.active_camera_index:
                cap.release()
                self._state.clear_visuals(resolution="0x0")
                reopened = self._open_camera(camera_cfg, runtime.desired_camera_index)
                if reopened is None:
                    self._state.set_active_camera_index(None)
                    self._state.set_vision_error(f"camera_open_failed:{runtime.desired_camera_index}")
                    time.sleep(REOPEN_WAIT_SECONDS)
                    continue
                cap = reopened
                self._state.set_active_camera_index(runtime.desired_camera_index)
                self._state.set_vision_error(None)
                read_fail_count = 0

            ok, frame = cap.read()
            capture_ms = (time.perf_counter() - capture_start) * 1000.0
            if not ok:
                read_fail_count += 1
                if read_fail_count >= READ_FAIL_REOPEN_THRESHOLD:
                    cap.release()
                    self._state.set_active_camera_index(None)
                    cap = self._open_camera(camera_cfg, runtime.desired_camera_index)
                    if cap is None:
                        self._state.set_vision_error(f"camera_reopen_failed:{runtime.desired_camera_index}")
                        time.sleep(REOPEN_WAIT_SECONDS)
                        continue
                    self._state.set_active_camera_index(runtime.desired_camera_index)
                    self._state.set_vision_error(None)
                    read_fail_count = 0
                time.sleep(0.01)
                continue
            read_fail_count = 0

            preprocess_start = time.perf_counter()
            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]
            self._frame_count += 1
            settings = self._state.get_runtime_settings_snapshot()
            preprocess_ms = (time.perf_counter() - preprocess_start) * 1000.0

            run_inference = (self._frame_count % settings.infer_every_n_frames) == 0
            dropped_count = self._state.metrics.snapshot()["dropped_inference_count"]
            target = None
            inference_ms = 0.0
            if run_inference:
                target_idx = None
                if settings.target_class != "all" and settings.target_class in self._detector.classes:
                    target_idx = [self._detector.classes.index(settings.target_class)]

                prediction = self._detector.infer(frame, target_classes=target_idx)
                inference_ms = prediction.inference_ms
                self._inference_count += 1
                target = self._selector.pick(prediction.detections, settings.target_class)
            else:
                dropped_count += 1

            tracked = self._tracker.update(target)
            render_start = time.perf_counter()
            output_frame = frame
            mask = None
            target_found = tracked is not None
            class_name = None
            class_conf = 0.0
            tracking_conf = 0.0
            centroid_x = 0
            centroid_y = 0
            mask_area = 0.0

            if tracked:
                det = tracked.detection
                output_frame = draw_detection_overlay(
                    frame,
                    det,
                    draw_mask=settings.draw_mask,
                    draw_bbox=settings.draw_bbox,
                    draw_contour=settings.draw_contour,
                    draw_label=settings.draw_label,
                    overlay_alpha=self._cfg["render"]["overlay_alpha"],
                )
                mask = det.segmentation_mask
                class_name = det.class_name
                class_conf = det.confidence
                tracking_conf = tracked.tracking_confidence
                centroid_x, centroid_y = det.centroid
                mask_area = det.visible_area
                self._state.mark_seen()
                self._state.metrics.mark_detection_found()
            else:
                cv2.putText(output_frame, "target not found", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 80, 255), 2)

            render_ms = (time.perf_counter() - render_start) * 1000.0
            self._state.update_visuals(output_frame, mask, f"{width}x{height}")

            fps_window_frames += 1
            elapsed = time.time() - fps_window_start
            frame_fps = fps_window_frames / elapsed if elapsed > 0 else 0.0
            if elapsed >= 1.0:
                self._state.set_vision_fps(frame_fps)
                fps_window_start = time.time()
                fps_window_frames = 0

            inf_fps = self._inference_count / max(1e-6, time.time() - service_start_ts)
            self._state.metrics.update(
                frame_fps=frame_fps,
                inference_fps=inf_fps,
                inference_ms=inference_ms,
                capture_ms=capture_ms,
                preprocess_ms=preprocess_ms,
                render_ms=render_ms,
                target_found=target_found,
                class_name=class_name,
                class_confidence=class_conf,
                tracking_confidence=tracking_conf,
                mask_area=mask_area,
                centroid_x=centroid_x,
                centroid_y=centroid_y,
                infer_every_n_frames=settings.infer_every_n_frames,
                current_target_class=settings.target_class,
                dropped_inference_count=dropped_count,
            )

        cap.release()
