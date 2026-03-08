"""Serviço isolado de visão computacional.

Responsável por captura de câmera, segmentação HSV, detecção do alvo e publicação
contínua de frames para a camada web. O módulo de servo é consumido apenas por interface
(ServoService), mantendo separação entre percepção e atuação.
"""

from __future__ import annotations

import time

import cv2

from .tracking import build_mask, compute_error_norm, compute_target_angle, detect_largest_blob

REOPEN_WAIT_SECONDS = 0.3
READ_FAIL_REOPEN_THRESHOLD = 20


class VisionService:
    """Executa o loop de visão de forma independente do restante da aplicação."""

    def __init__(self, cfg: dict, state, servo_service):
        self._cfg = cfg
        self._state = state
        self._servo_service = servo_service

    def _open_camera(self, camera_cfg: dict, camera_index: int):
        """Abre câmera e aplica parâmetros operacionais de baixa latência."""
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
        """Loop principal de visão (thread dedicada)."""
        camera_cfg = self._cfg["camera"]
        tracking_cfg = self._cfg["tracking"]
        servo_cfg = self._cfg["servo"]
        debug_cfg = self._cfg["debug"]

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
        scan_direction = 1.0
        frame_count = 0
        read_fail_count = 0

        fps_window_start = time.time()
        fps_window_frames = 0

        while self._state.running:
            runtime = self._state.get_runtime_snapshot()
            if runtime.desired_camera_index != runtime.active_camera_index:
                cap.release()
                self._state.clear_visuals(resolution="0x0")
                next_index = runtime.desired_camera_index
                reopened = self._open_camera(camera_cfg, next_index)
                if reopened is None:
                    self._state.set_active_camera_index(None)
                    self._state.set_vision_error(f"camera_open_failed:{next_index}")
                    time.sleep(REOPEN_WAIT_SECONDS)
                    continue
                cap = reopened
                self._state.set_active_camera_index(next_index)
                self._state.set_vision_error(None)
                read_fail_count = 0

            ok, frame = cap.read()
            if not ok:
                read_fail_count += 1
                if read_fail_count >= READ_FAIL_REOPEN_THRESHOLD:
                    self._state.set_active_camera_index(None)
                    cap.release()
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

            frame_count += 1
            if debug_cfg["frame_skip"] > 0 and (frame_count % (debug_cfg["frame_skip"] + 1)) != 1:
                continue

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = build_mask(hsv, runtime.color_name)
            detection = detect_largest_blob(mask, tracking_cfg["area_min"])

            active_index = self._state.get_runtime_snapshot().active_camera_index
            status = f"cam={active_index} mode={runtime.mode} color={runtime.color_name} angle={runtime.target_angle:.1f}"
            if detection:
                x, y, ww, hh, area = detection
                tx, ty = x + ww // 2, y + hh // 2
                error_norm = compute_error_norm(tx, w)

                cv2.rectangle(frame, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
                cv2.circle(frame, (tx, ty), 5, (0, 255, 255), -1)
                cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 1)

                status = f"{status} area={int(area)} err={error_norm:+.2f}"
                self._state.mark_seen()

                runtime = self._state.get_runtime_snapshot()
                if runtime.mode == "auto" and runtime.servo_enabled:
                    desired = compute_target_angle(
                        runtime.target_angle,
                        error_norm,
                        tracking_cfg["kp"],
                        tracking_cfg["deadband"],
                        servo_cfg["min_angle"],
                        servo_cfg["max_angle"],
                    )
                    self._state.runtime.target_angle = self._servo_service.set_angle(desired)

            runtime = self._state.get_runtime_snapshot()
            if tracking_cfg["scan_on_target_loss"] and runtime.mode == "auto":
                loss_ms = (time.time() - runtime.last_seen_ts) * 1000.0
                if loss_ms >= tracking_cfg["scan_after_ms"]:
                    scan_target = runtime.target_angle + scan_direction * 1.5
                    if scan_target >= servo_cfg["max_angle"] or scan_target <= servo_cfg["min_angle"]:
                        scan_direction *= -1.0
                    self._state.runtime.target_angle = self._servo_service.set_angle(scan_target)

            fps_window_frames += 1
            elapsed = time.time() - fps_window_start
            if elapsed >= 1.0:
                # FPS da pipeline de visão para observabilidade na web geral.
                self._state.set_vision_fps(round(fps_window_frames / max(elapsed, 1e-6), 2))
                fps_window_frames = 0
                fps_window_start = time.time()

            cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            self._state.update_visuals(frame, mask, f"{w}x{h}")

        cap.release()
        self._state.set_vision_running(False)
