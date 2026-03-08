"""Captura da câmera e loop de tracking sem bloqueio da web."""

from __future__ import annotations

import time

import cv2

from .tracking import build_mask, compute_error_norm, compute_target_angle, detect_largest_blob


REOPEN_WAIT_SECONDS = 0.3
READ_FAIL_REOPEN_THRESHOLD = 20


def _open_camera(camera_cfg: dict, camera_index: int):
    """Abre e configura um device de vídeo retornando o capture pronto para uso."""
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_cfg["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_cfg["height"])
    cap.set(cv2.CAP_PROP_FPS, camera_cfg["fps"])
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        cap.release()
        return None
    return cap


def run_tracking_loop(cfg: dict, state, servo_backend):
    camera_cfg = cfg["camera"]
    tracking_cfg = cfg["tracking"]
    servo_cfg = cfg["servo"]
    debug_cfg = cfg["debug"]

    state.set_active_camera_index(None)
    desired_camera_index = state.get_runtime_snapshot().desired_camera_index
    cap = _open_camera(camera_cfg, desired_camera_index)
    if cap is None:
        raise RuntimeError(f"Não consegui abrir câmera index={desired_camera_index}")

    state.set_active_camera_index(desired_camera_index)
    state.runtime.target_angle = servo_backend.set_angle(servo_cfg["center_angle"], force=True)
    scan_direction = 1.0
    frame_count = 0
    read_fail_count = 0

    while state.running:
        runtime = state.get_runtime_snapshot()
        if runtime.desired_camera_index != runtime.active_camera_index:
            cap.release()
            state.clear_visuals(resolution="0x0")
            next_index = runtime.desired_camera_index
            reopened = _open_camera(camera_cfg, next_index)
            if reopened is None:
                state.set_active_camera_index(None)
                time.sleep(REOPEN_WAIT_SECONDS)
                continue
            cap = reopened
            state.set_active_camera_index(next_index)
            read_fail_count = 0

        ok, frame = cap.read()
        if not ok:
            read_fail_count += 1
            if read_fail_count >= READ_FAIL_REOPEN_THRESHOLD:
                state.set_active_camera_index(None)
                cap.release()
                cap = _open_camera(camera_cfg, runtime.desired_camera_index)
                if cap is None:
                    time.sleep(REOPEN_WAIT_SECONDS)
                    continue
                state.set_active_camera_index(runtime.desired_camera_index)
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

        active_index = state.get_runtime_snapshot().active_camera_index
        status = f"cam={active_index} mode={runtime.mode} color={runtime.color_name} angle={runtime.target_angle:.1f}"
        if detection:
            x, y, ww, hh, area = detection
            tx, ty = x + ww // 2, y + hh // 2
            error_norm = compute_error_norm(tx, w)

            cv2.rectangle(frame, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
            cv2.circle(frame, (tx, ty), 5, (0, 255, 255), -1)
            cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 1)

            status = f"{status} area={int(area)} err={error_norm:+.2f}"
            state.mark_seen()

            runtime = state.get_runtime_snapshot()
            if runtime.mode == "auto" and runtime.servo_enabled:
                desired = compute_target_angle(
                    runtime.target_angle,
                    error_norm,
                    tracking_cfg["kp"],
                    tracking_cfg["deadband"],
                    servo_cfg["min_angle"],
                    servo_cfg["max_angle"],
                )
                state.runtime.target_angle = servo_backend.set_angle(desired)

        runtime = state.get_runtime_snapshot()
        if tracking_cfg["scan_on_target_loss"] and runtime.mode == "auto":
            loss_ms = (time.time() - runtime.last_seen_ts) * 1000.0
            if loss_ms >= tracking_cfg["scan_after_ms"]:
                scan_target = runtime.target_angle + scan_direction * 1.5
                if scan_target >= servo_cfg["max_angle"] or scan_target <= servo_cfg["min_angle"]:
                    scan_direction *= -1.0
                state.runtime.target_angle = servo_backend.set_angle(scan_target)

        cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        state.update_visuals(frame, mask, f"{w}x{h}")

    cap.release()
