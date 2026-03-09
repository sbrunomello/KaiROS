"""Flask app + UI simples para controle e monitoramento."""

from __future__ import annotations

import time

from flask import Flask, Response, jsonify, render_template_string, request

from .tracking import COLOR_PRESETS

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>KaiROS Bot Runtime V0</title>
  <style>
    body { background:#111; color:#eee; font-family:Arial,sans-serif; margin:16px; }
    .row { display:flex; gap:16px; flex-wrap:wrap; }
    .card { background:#1b1b1b; border-radius:12px; padding:12px; }
    img { width:100%; max-width:520px; border-radius:8px; }
    button, select, input { margin:4px; padding:8px 12px; border-radius:8px; border:1px solid #333; background:#222; color:#eee; }
    label { display:inline-flex; align-items:center; gap:8px; margin-right:8px; }
    code { background:#222; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <h1>KaiROS Bot Runtime V0 - Modular</h1>
  <p>
    mode=<code id="mode"></code>
    color=<code id="color"></code>
    camera=<code id="camera"></code>
    servo=<code id="servo"></code>
    angle=<code id="angle"></code>
    res=<code id="res"></code>
    vision=<code id="visionStatus"></code>
    vision_fps=<code id="visionFps"></code>
  </p>
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
  <div class="card">
    <h3>Tracking em tempo real</h3>
    <label>
      Device:
      <input id="cameraIndexInput" type="number" min="0" step="1" placeholder="0" style="width:80px;"/>
      <button onclick="setCamera()">Aplicar</button>
    </label>
    <label>
      Target:
      <select id="targetColor" onchange="setTargetColor()"></select>
    </label>
    <small id="feedback"></small>
  </div>
  <script>
    async function post(url, body={}) {
      const response = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if(!response.ok){
        const data = await response.json().catch(()=>({error:'request_failed'}));
        throw new Error(data.error || 'request_failed');
      }
      return response.json();
    }

    function showFeedback(message, isError=false){
      feedback.textContent = message;
      feedback.style.color = isError ? '#ff6b6b' : '#7dff9f';
      setTimeout(()=>{ feedback.textContent=''; }, 1800);
    }

    async function setAngle(angle){
      try {
        await post('/api/servo/angle',{angle});
        showFeedback(`Ângulo atualizado para ${angle}°`);
      } catch (error) {
        showFeedback(`Falha ao atualizar ângulo: ${error.message}`, true);
      }
    }

    async function setCamera(){
      const value = Number.parseInt(cameraIndexInput.value, 10);
      if(Number.isNaN(value) || value < 0){
        showFeedback('Informe um índice de câmera válido (>= 0).', true);
        return;
      }
      try {
        await post('/api/camera/index', { index: value });
        showFeedback(`Solicitada troca para câmera ${value}.`);
        await refresh();
      } catch (error) {
        showFeedback(`Falha ao trocar câmera: ${error.message}`, true);
      }
    }

    async function setTargetColor(){
      const colorName = targetColor.value;
      try {
        await post('/api/tracking/color', { color: colorName });
        showFeedback(`Target alterado para ${colorName}.`);
        await refresh();
      } catch (error) {
        showFeedback(`Falha ao alterar target: ${error.message}`, true);
      }
    }

    async function refresh(){
      const r = await fetch('/health');
      const d = await r.json();
      mode.textContent = d.mode;
      color.textContent = d.color;
      camera.textContent = `${d.active_camera_index ?? '-'} (wanted ${d.desired_camera_index})`;
      servo.textContent = d.servo_enabled;
      angle.textContent = d.target_angle.toFixed(1);
      res.textContent = d.resolution;
      visionStatus.textContent = d.modules.vision.running ? "up" : `down (${d.modules.vision.last_error || "unknown"})`;
      visionFps.textContent = d.modules.vision.fps.toFixed(2);

      if(document.activeElement !== cameraIndexInput){
        cameraIndexInput.value = d.desired_camera_index;
      }

      if(targetColor.options.length === 0){
        d.available_colors.forEach((colorOpt) => {
          const option = document.createElement('option');
          option.value = colorOpt;
          option.textContent = colorOpt;
          targetColor.appendChild(option);
        });
      }
      targetColor.value = d.color;
    }

    setInterval(refresh, 700);
    refresh();
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


def build_app(cfg: dict, state, servo_service):
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
        runtime = state.get_runtime_snapshot()
        return jsonify(
            ok=True,
            mode=runtime.mode,
            color=runtime.color_name,
            available_colors=sorted(COLOR_PRESETS.keys()),
            servo_enabled=runtime.servo_enabled,
            target_angle=runtime.target_angle,
            resolution=runtime.resolution,
            last_seen_ts=runtime.last_seen_ts,
            desired_camera_index=runtime.desired_camera_index,
            active_camera_index=runtime.active_camera_index,
            modules={
                "vision": {
                    "running": runtime.vision_running,
                    "last_error": runtime.vision_last_error,
                    "fps": runtime.vision_fps,
                },
                "servo": {
                    "enabled": runtime.servo_enabled,
                },
            },
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
        state.runtime.target_angle = servo_service.set_angle(angle, force=True)
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

        state.runtime.target_angle = servo_service.set_angle(angle, force=True)
        return jsonify(ok=True, target_angle=state.runtime.target_angle)

    @app.post("/api/camera/index")
    def set_camera_index():
        payload = request.get_json(silent=True) or {}
        camera_index = payload.get("index")
        if camera_index is None:
            return jsonify(ok=False, error="missing_field_index"), 400

        try:
            camera_index = int(camera_index)
        except (TypeError, ValueError):
            return jsonify(ok=False, error="invalid_index"), 400

        if camera_index < 0:
            return jsonify(ok=False, error="index_must_be_non_negative"), 400

        state.set_desired_camera_index(camera_index)
        return jsonify(ok=True, desired_camera_index=camera_index)

    @app.post("/api/tracking/color")
    def set_tracking_color():
        payload = request.get_json(silent=True) or {}
        color_name = payload.get("color")
        if color_name is None:
            return jsonify(ok=False, error="missing_field_color"), 400

        if color_name not in COLOR_PRESETS:
            return jsonify(ok=False, error="invalid_color", available_colors=sorted(COLOR_PRESETS.keys())), 400

        state.set_color(color_name)
        return jsonify(ok=True, color=color_name)

    return app
