import argparse
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np
from flask import Flask, Response, render_template_string

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>KaiROS Turret</title>
  <style>
    body { background:#111; color:#eee; font-family:Arial,sans-serif; margin:20px; }
    .row { display:flex; gap:20px; flex-wrap:wrap; }
    .card { background:#1b1b1b; padding:16px; border-radius:12px; }
    img { max-width:100%; border-radius:8px; }
    code { background:#222; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <h1>KaiROS Turret Tracking</h1>
  <p>
    cor=<code>{{ color_name }}</code>
    servo=<code>{{ servo_enabled }}</code>
    stream=<code>/video_feed</code>
  </p>
  <div class="row">
    <div class="card">
      <h3>Vídeo</h3>
      <img src="/video_feed">
    </div>
    <div class="card">
      <h3>Máscara</h3>
      <img src="/mask_feed">
    </div>
  </div>
</body>
</html>
"""

COLOR_PRESETS = {
    "blue": [((100, 120, 70), (130, 255, 255))],
    "green": [((35, 80, 60), (85, 255, 255))],
    "yellow": [((20, 100, 100), (35, 255, 255))],
    "red": [
        ((0, 120, 70), (10, 255, 255)),
        ((170, 120, 70), (179, 255, 255)),
    ],
}

TARGET_FILE = "/tmp/kairos_servo_target"


@dataclass
class Config:
    camera_index: int
    width: int
    height: int
    fps: int
    color_name: str
    servo_enabled: bool
    center_angle: float
    min_angle: float
    max_angle: float
    kp: float
    deadband: float
    area_min: int
    bind: str
    port: int
    jpeg_quality: int
    stream_sleep: float
    servo_file_write_interval: float
    frame_skip: int


class SharedState:
    def __init__(self, config: Config):
        self.config = config
        self.frame = None
        self.mask = None
        self.lock = threading.Lock()

        self.current_angle = config.center_angle
        self.target_angle = config.center_angle
        self.last_target_write_ts = 0.0
        self.last_seen_ts = 0.0

        self.running = True

    def write_target_angle(self, angle: float, force: bool = False):
        if not self.config.servo_enabled:
            return

        angle = max(self.config.min_angle, min(self.config.max_angle, angle))
        now = time.time()

        if not force and (now - self.last_target_write_ts) < self.config.servo_file_write_interval:
            return

        if not force and abs(angle - self.target_angle) < 1.0:
            return

        self.target_angle = angle

        try:
            with open(TARGET_FILE, "w", encoding="utf-8") as fp:
                fp.write(f"{angle:.2f}\n")
            self.last_target_write_ts = now
        except Exception as e:
            print(f"[WARN] falha ao escrever target angle: {e}")

    def get_jpeg_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            ok, buf = cv2.imencode(
                ".jpg",
                self.frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.config.jpeg_quality],
            )
            if not ok:
                return None
            return buf.tobytes()

    def get_jpeg_mask(self):
        with self.lock:
            if self.mask is None:
                return None
            mask_bgr = cv2.cvtColor(self.mask, cv2.COLOR_GRAY2BGR)
            ok, buf = cv2.imencode(
                ".jpg",
                mask_bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.config.jpeg_quality],
            )
            if not ok:
                return None
            return buf.tobytes()


def build_mask(hsv: np.ndarray, color_name: str) -> np.ndarray:
    ranges = COLOR_PRESETS[color_name]
    combined = None

    for lower, upper in ranges:
        part = cv2.inRange(
            hsv,
            np.array(lower, dtype=np.uint8),
            np.array(upper, dtype=np.uint8),
        )
        combined = part if combined is None else cv2.bitwise_or(combined, part)

    kernel = np.ones((5, 5), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
    return combined


def tracking_loop(state: SharedState):
    cfg = state.config

    cap = cv2.VideoCapture(cfg.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
    cap.set(cv2.CAP_PROP_FPS, cfg.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise RuntimeError(f"Não consegui abrir a câmera index={cfg.camera_index}")

    # centraliza ao subir
    state.write_target_angle(cfg.center_angle, force=True)
    frame_count = 0

    while state.running:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        frame_count += 1
        if cfg.frame_skip > 0 and (frame_count % (cfg.frame_skip + 1)) != 1:
            continue

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        center_x = w // 2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = build_mask(hsv, cfg.color_name)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        status = f"color={cfg.color_name} angle={state.target_angle:.1f}"

        if contours:
            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)

            if area >= cfg.area_min:
                x, y, ww, hh = cv2.boundingRect(c)
                target_x = x + ww // 2
                target_y = y + hh // 2

                error_px = target_x - center_x
                error_norm = error_px / max(1, center_x)

                cv2.rectangle(frame, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
                cv2.circle(frame, (target_x, target_y), 5, (0, 255, 255), -1)
                cv2.line(frame, (center_x, 0), (center_x, h), (255, 255, 255), 1)

                status = (
                    f"color={cfg.color_name} "
                    f"area={int(area)} "
                    f"err={error_norm:+.2f} "
                    f"target={state.target_angle:.1f}"
                )

                if abs(error_norm) > cfg.deadband:
                    desired = state.target_angle + (cfg.kp * error_norm)
                    desired = max(cfg.min_angle, min(cfg.max_angle, desired))
                    state.write_target_angle(desired)

                state.last_seen_ts = time.time()

        cv2.putText(
            frame,
            status,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

        with state.lock:
            state.frame = frame
            state.mask = mask

    cap.release()


def mjpeg_generator(get_bytes_fn, sleep_s: float):
    while True:
        frame = get_bytes_fn()
        if frame is None:
            time.sleep(0.03)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )
        time.sleep(sleep_s)


def build_app(state: SharedState):
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template_string(
            HTML,
            color_name=state.config.color_name,
            servo_enabled=state.config.servo_enabled,
        )

    @app.route("/video_feed")
    def video_feed():
        return Response(
            mjpeg_generator(state.get_jpeg_frame, state.config.stream_sleep),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/mask_feed")
    def mask_feed():
        return Response(
            mjpeg_generator(state.get_jpeg_mask, state.config.stream_sleep),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/health")
    def health():
        return {
            "ok": True,
            "color": state.config.color_name,
            "servo_enabled": state.config.servo_enabled,
            "target_angle": state.target_angle,
        }

    return app


def parse_args():
    parser = argparse.ArgumentParser(description="KaiROS low-lag turret web tracking")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=424)
    parser.add_argument("--height", type=int, default=240)
    parser.add_argument("--fps", type=int, default=15)

    parser.add_argument("--color", choices=sorted(COLOR_PRESETS.keys()), default="blue")
    parser.add_argument("--no-servo", action="store_true")

    parser.add_argument("--center-angle", type=float, default=90)
    parser.add_argument("--min-angle", type=float, default=40)
    parser.add_argument("--max-angle", type=float, default=140)

    parser.add_argument("--kp", type=float, default=18.0)
    parser.add_argument("--deadband", type=float, default=0.10)
    parser.add_argument("--area-min", type=int, default=350)

    parser.add_argument("--jpeg-quality", type=int, default=60)
    parser.add_argument("--stream-sleep", type=float, default=0.05)
    parser.add_argument("--servo-file-write-interval-ms", type=int, default=80)
    parser.add_argument("--frame-skip", type=int, default=0)

    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)

    return parser.parse_args()


def main():
    args = parse_args()

    config = Config(
        camera_index=args.camera_index,
        width=args.width,
        height=args.height,
        fps=args.fps,
        color_name=args.color,
        servo_enabled=not args.no_servo,
        center_angle=args.center_angle,
        min_angle=args.min_angle,
        max_angle=args.max_angle,
        kp=args.kp,
        deadband=args.deadband,
        area_min=args.area_min,
        bind=args.bind,
        port=args.port,
        jpeg_quality=args.jpeg_quality,
        stream_sleep=args.stream_sleep,
        servo_file_write_interval=args.servo_file_write_interval_ms / 1000.0,
        frame_skip=args.frame_skip,
    )

    state = SharedState(config)

    t = threading.Thread(target=tracking_loop, args=(state,), daemon=True)
    t.start()

    app = build_app(state)
    print(f"[INFO] web: http://{config.bind}:{config.port}")
    print(f"[INFO] color: {config.color_name}")
    print(f"[INFO] servo enabled: {config.servo_enabled}")
    app.run(host=config.bind, port=config.port, threaded=True)


if __name__ == "__main__":
    main()
