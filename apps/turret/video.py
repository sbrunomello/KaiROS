"""Captura da câmera e loop de tracking sem bloqueio da web."""

from __future__ import annotations

import time

import cv2

from .tracking import build_mask, compute_error_norm, compute_target_angle, detect_largest_blob


def run_tracking_loop(cfg: dict, state, servo_backend):
    camera_cfg = cfg["camera"]
    tracking_cfg = cfg["tracking"]
    servo_cfg = cfg["servo"]
    debug_cfg = cfg["debug"]

    cap = cv2.VideoCapture(camera_cfg["index"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_cfg["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_cfg["height"])
    cap.set(cv2.CAP_PROP_FPS, camera_cfg["fps"])
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise RuntimeError(f"Não consegui abrir câmera index={camera_cfg['index']}")

    state.runtime.target_angle = servo_backend.set_angle(servo_cfg["center_angle"], force=True)
    scan_direction = 1.0
    frame_count = 0

    while state.running:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        frame_count += 1
        if debug_cfg["frame_skip"] > 0 and (frame_count % (debug_cfg["frame_skip"] + 1)) != 1:
            continue

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = build_mask(hsv, state.runtime.color_name)
        detection = detect_largest_blob(mask, tracking_cfg["area_min"])

        status = f"mode={state.runtime.mode} color={state.runtime.color_name} angle={state.runtime.target_angle:.1f}"
        if detection:
            x, y, ww, hh, area = detection
            tx, ty = x + ww // 2, y + hh // 2
            error_norm = compute_error_norm(tx, w)

            cv2.rectangle(frame, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
            cv2.circle(frame, (tx, ty), 5, (0, 255, 255), -1)
            cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 1)

            status = f"{status} area={int(area)} err={error_norm:+.2f}"
            state.mark_seen()

            if state.runtime.mode == "auto" and state.runtime.servo_enabled:
                desired = compute_target_angle(
                    state.runtime.target_angle,
                    error_norm,
                    tracking_cfg["kp"],
                    tracking_cfg["deadband"],
                    servo_cfg["min_angle"],
                    servo_cfg["max_angle"],
                )
                state.runtime.target_angle = servo_backend.set_angle(desired)

        if tracking_cfg["scan_on_target_loss"] and state.runtime.mode == "auto":
            loss_ms = (time.time() - state.runtime.last_seen_ts) * 1000.0
            if loss_ms >= tracking_cfg["scan_after_ms"]:
                scan_target = state.runtime.target_angle + scan_direction * 1.5
                if scan_target >= servo_cfg["max_angle"] or scan_target <= servo_cfg["min_angle"]:
                    scan_direction *= -1.0
                state.runtime.target_angle = servo_backend.set_angle(scan_target)

        cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        state.update_visuals(frame, mask, f"{w}x{h}")

    cap.release()
