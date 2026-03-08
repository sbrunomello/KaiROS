"""Flask app + UI simples para controle e monitoramento."""

from __future__ import annotations

import time

from flask import Flask, Response, jsonify, render_template_string, request

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>KaiROS Turret V0</title>
  <style>
    body { background:#111; color:#eee; font-family:Arial,sans-serif; margin:16px; }
    .row { display:flex; gap:16px; flex-wrap:wrap; }
    .card { background:#1b1b1b; border-radius:12px; padding:12px; }
    img { width:100%; max-width:520px; border-radius:8px; }
    button { margin:4px; padding:8px 12px; }
    code { background:#222; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <h1>KaiROS Turret V0</h1>
  <p>mode=<code id="mode"></code> color=<code id="color"></code> servo=<code id="servo"></code> angle=<code id="angle"></code> res=<code id="res"></code></p>
  <div class="row">
    <div class="card"><h3>Video</h3><img src="/video_feed" /></div>
    <div class="card"><h3>Mask</h3><img src="/mask_feed" /></div>
  </div>
  <div class="card">
    <button onclick="post('/api/mode/auto')">AUTO</button>
    <button onclick="post('/api/mode/manual')">MANUAL</button>
    <button onclick="post('/api/servo/center')">CENTER</button>
    <button onclick="setAngle(70)">70°</button>
    <button onclick="setAngle(90)">90°</button>
    <button onclick="setAngle(110)">110°</button>
  </div>
  <script>
    async function post(url, body={}) { await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); }
    async function setAngle(angle){ await post('/api/servo/angle',{angle}); }
    async function refresh(){
      const r = await fetch('/health'); const d = await r.json();
      mode.textContent=d.mode; color.textContent=d.color; servo.textContent=d.servo_enabled; angle.textContent=d.target_angle.toFixed(1); res.textContent=d.resolution;
    }
    setInterval(refresh,1000); refresh();
  </script>
</body>
</html>
"""


def mjpeg_generator(get_frame, sleep_ms: int):
    while True:
        frame = get_frame()
        if frame is None:
            time.sleep(0.03)
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        time.sleep(sleep_ms / 1000.0)


def build_app(cfg: dict, state, servo_backend):
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template_string(HTML)

    @app.get("/video_feed")
    def video_feed():
        return Response(mjpeg_generator(state.get_jpeg_frame, cfg["web"]["stream_sleep_ms"]), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/mask_feed")
    def mask_feed():
        return Response(mjpeg_generator(state.get_jpeg_mask, cfg["web"]["stream_sleep_ms"]), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/health")
    def health():
        return jsonify(
            ok=True,
            mode=state.runtime.mode,
            color=state.runtime.color_name,
            servo_enabled=state.runtime.servo_enabled,
            target_angle=state.runtime.target_angle,
            resolution=state.runtime.resolution,
            last_seen_ts=state.runtime.last_seen_ts,
        )

    @app.post("/api/mode/auto")
    def set_auto():
        state.runtime.mode = "auto"
        return jsonify(ok=True, mode=state.runtime.mode)

    @app.post("/api/mode/manual")
    def set_manual():
        state.runtime.mode = "manual"
        return jsonify(ok=True, mode=state.runtime.mode)

    @app.post("/api/servo/center")
    def center_servo():
        angle = cfg["servo"]["center_angle"]
        state.runtime.target_angle = servo_backend.set_angle(angle, force=True)
        return jsonify(ok=True, target_angle=state.runtime.target_angle)

    @app.post("/api/servo/angle")
    def set_servo_angle():
        payload = request.get_json(silent=True) or {}
        angle = payload.get("angle")
        if angle is None:
            return jsonify(ok=False, error="missing_field_angle"), 400
        try:
            angle = float(angle)
        except (TypeError, ValueError):
            return jsonify(ok=False, error="invalid_angle"), 400

        if state.runtime.mode != "manual":
            return jsonify(ok=False, error="mode_must_be_manual"), 409

        state.runtime.target_angle = servo_backend.set_angle(angle, force=True)
        return jsonify(ok=True, target_angle=state.runtime.target_angle)

    return app
