"""Flask app + UI web com menu legado e reconhecimento modular."""

from __future__ import annotations

import time

from flask import Flask, Response, jsonify, render_template_string, request

HTML = """
<!doctype html><html><head><meta charset="utf-8"/><title>KaiROS Vision</title>
<style>
body { background:#111; color:#eee; font-family:Arial,sans-serif; margin:16px; }
.row { display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start; }
.card { background:#1b1b1b; border-radius:12px; padding:12px; min-width:280px; }
img { width:100%; max-width:720px; border-radius:8px; }
button, select, input { margin:4px; padding:8px 12px; border-radius:8px; border:1px solid #333; background:#222; color:#eee; }
label { display:flex; align-items:center; justify-content:space-between; margin:8px 0; gap:10px; }
small.warn { color:#ff7e7e; font-weight:bold; }
.hidden { display:none; }
</style></head>
<body>
<h2>KaiROS - Vision Console</h2>
<div class="row">
  <div class="card"><h3>Video</h3><img src="/video_feed" /></div>
  <div class="card"><h3>Mask Stream</h3><img src="/mask_feed" /></div>
</div>
<div class="row">
  <div class="card">
    <h3>Reconhecimento (modular)</h3>
    <label>Modo de reconhecimento<select id="recognitionMode"></select></label>
    <div id="yoloControls">
      <label>Classe alvo<select id="targetClass"></select></label>
      <label>Inferência a cada N frames<input id="inferN" type="number" min="1" step="1"/></label>
      <label><span>Mostrar máscara</span><input id="drawMask" type="checkbox"/></label>
      <label><span>Mostrar bounding box</span><input id="drawBbox" type="checkbox"/></label>
      <label><span>Mostrar contorno</span><input id="drawContour" type="checkbox"/></label>
      <label><span>Mostrar label/conf</span><input id="drawLabel" type="checkbox"/></label>
    </div>
    <div id="colorControls">
      <label>Cor alvo<select id="targetColor"></select></label>
    </div>
    <button onclick="saveRuntime()">Aplicar runtime</button>
    <small id="feedback"></small>
  </div>
  <div class="card">
    <h3>Câmera e controle (sempre visível)</h3>
    <label>Camera index<input id="cameraIndex" type="number" step="1"/></label>
    <label>Modo de controle<select id="controlMode"><option value="auto">auto</option><option value="manual">manual</option></select></label>
    <label>Ângulo manual<input id="manualAngle" type="number" min="0" max="180" step="1"/></label>
    <button onclick="applyCamera()">Aplicar câmera</button>
    <button onclick="applyMode()">Aplicar modo</button>
    <button onclick="centerServo()">Centralizar servo</button>
    <button onclick="applyManualAngle()">Enviar ângulo</button>
  </div>
  <div class="card">
    <h3>Métricas</h3>
    <div>FPS frame: <b id="frameFps"></b></div>
    <div>Inferência média (ms): <b id="infAvg"></b></div>
    <div>Inferência/s: <b id="infFps"></b></div>
    <div>Classe alvo atual: <b id="targetNow"></b></div>
    <div>Status alvo: <b id="targetStatus"></b></div>
    <div>Confidence: <b id="conf"></b></div>
    <div>Área máscara: <b id="area"></b></div>
    <div>Cam ativa: <b id="activeCam"></b></div>
    <div>Modo reconhecimento: <b id="activeRecognition"></b></div>
    <small id="targetWarn" class="warn"></small>
  </div>
</div>
<script>
async function jget(url){ const r = await fetch(url); return r.json(); }
async function jpost(url, body){ const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); return r.json(); }
function toast(msg, err=false){ feedback.textContent=msg; feedback.style.color = err?'#ff6b6b':'#8dff95'; setTimeout(()=>feedback.textContent='',2500); }

function syncVisibility(){
  const mode = recognitionMode.value;
  yoloControls.classList.toggle('hidden', mode !== 'yolo');
  colorControls.classList.toggle('hidden', mode !== 'color');
}

async function loadCapabilities(){
  const d = await jget('/api/vision/capabilities');
  recognitionMode.innerHTML='';
  d.recognition_modes.forEach((name)=>{ const o=document.createElement('option'); o.value=name; o.textContent=name; recognitionMode.appendChild(o); });
  targetClass.innerHTML='';
  d.classes.forEach((name)=>{ const o=document.createElement('option'); o.value=name; o.textContent=name; targetClass.appendChild(o); });
  targetColor.innerHTML='';
  d.color_presets.forEach((name)=>{ const o=document.createElement('option'); o.value=name; o.textContent=name; targetColor.appendChild(o); });
}

async function loadRuntime(){
  const d = await jget('/api/vision/runtime');
  recognitionMode.value=d.recognition_mode; targetClass.value=d.target_class; targetColor.value=d.target_color;
  inferN.value=d.infer_every_n_frames; drawMask.checked=d.draw_mask; drawBbox.checked=d.draw_bbox; drawContour.checked=d.draw_contour; drawLabel.checked=d.draw_label;
  syncVisibility();
}

async function loadSystem(){
  const d = await jget('/api/system/state');
  cameraIndex.value = d.desired_camera_index;
  controlMode.value = d.mode;
  manualAngle.value = d.target_angle.toFixed(0);
}

async function saveRuntime(){
  const body={ recognition_mode: recognitionMode.value, target_class:targetClass.value, target_color: targetColor.value, infer_every_n_frames:Number(inferN.value), draw_mask:drawMask.checked, draw_bbox:drawBbox.checked, draw_contour:drawContour.checked, draw_label:drawLabel.checked };
  const r = await jpost('/api/vision/runtime', body);
  toast(r.ok ? 'Runtime atualizado' : 'Falha ao atualizar', !r.ok);
}

async function applyCamera(){
  const r = await jpost('/api/camera/select', { camera_index: Number(cameraIndex.value) });
  toast(r.ok ? 'Câmera atualizada' : 'Falha ao atualizar câmera', !r.ok);
}

async function applyMode(){
  const mode = controlMode.value;
  const r = await fetch(mode === 'auto' ? '/api/mode/auto' : '/api/mode/manual', { method:'POST' });
  const d = await r.json();
  toast(d.ok ? 'Modo atualizado' : 'Falha ao atualizar modo', !d.ok);
}

async function centerServo(){
  const d = await jpost('/api/servo/center', {});
  toast(d.ok ? 'Servo centralizado' : 'Falha ao centralizar', !d.ok);
}

async function applyManualAngle(){
  const d = await jpost('/api/servo/angle', { angle: Number(manualAngle.value) });
  toast(d.ok ? 'Ângulo enviado' : `Falha: ${d.error || 'erro'}`, !d.ok);
}

async function refreshMetrics(){
  const m = await jget('/api/vision/metrics');
  const s = await jget('/api/system/state');
  frameFps.textContent=(m.frame_fps||0).toFixed(2); infAvg.textContent=(m.inference_avg_ms||0).toFixed(2); infFps.textContent=(m.inference_fps||0).toFixed(2);
  targetNow.textContent=m.current_target_class||'-'; targetStatus.textContent=m.target_found?'encontrado':'perdido';
  conf.textContent=(m.class_confidence||0).toFixed(2); area.textContent=(m.mask_area||0).toFixed(1);
  activeCam.textContent = s.active_camera_index === null ? '-' : String(s.active_camera_index);
  activeRecognition.textContent = s.recognition_mode;
  targetWarn.textContent=m.target_found ? '' : 'target not found';
}

recognitionMode.addEventListener('change', syncVisibility);
setInterval(refreshMetrics, 700);
(async()=>{ await loadCapabilities(); await loadRuntime(); await loadSystem(); await refreshMetrics(); })();
</script>
</body></html>
"""


def mjpeg_generator(get_frame, sleep_ms: int):
    while True:
        frame = get_frame()
        if frame is None:
            time.sleep(0.03)
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        time.sleep(sleep_ms / 1000.0)


def build_app(cfg: dict, state, servo_service, classes, recognition_modes=None, color_presets=None):
    app = Flask(__name__)
    recognition_modes = recognition_modes or ["yolo", "color"]
    color_presets = color_presets or ["blue", "green", "yellow", "red"]

    @app.get("/")
    def index():
        return render_template_string(HTML)

    @app.get("/video_feed")
    def video_feed():
        return Response(mjpeg_generator(state.get_jpeg_frame, cfg["web"]["stream_sleep_ms"]), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/mask_feed")
    def mask_feed():
        return Response(mjpeg_generator(state.get_jpeg_mask, cfg["web"]["stream_sleep_ms"]), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/system/state")
    def system_state():
        runtime = state.get_runtime_snapshot()
        return jsonify(
            ok=True,
            mode=runtime.mode,
            target_angle=runtime.target_angle,
            desired_camera_index=runtime.desired_camera_index,
            active_camera_index=runtime.active_camera_index,
            recognition_mode=runtime.recognition_mode,
        )

    @app.post("/api/camera/select")
    def update_camera():
        payload = request.get_json(silent=True) or {}
        try:
            camera_index = int(payload.get("camera_index"))
        except (TypeError, ValueError):
            return jsonify(ok=False, error="invalid_camera_index"), 400
        state.set_desired_camera_index(camera_index)
        return jsonify(ok=True, desired_camera_index=camera_index)

    @app.get("/health")
    def health():
        runtime = state.get_runtime_snapshot()
        metrics = state.metrics.snapshot()
        return jsonify(ok=True, mode=runtime.mode, target_angle=runtime.target_angle, modules={"vision": {"running": runtime.vision_running, "last_error": runtime.vision_last_error, "fps": runtime.vision_fps}}, metrics=metrics)

    @app.get("/api/vision/capabilities")
    def vision_capabilities():
        return jsonify(ok=True, recognition_modes=recognition_modes, classes=["all", *classes], color_presets=color_presets)

    @app.get("/api/vision/classes")
    def vision_classes():
        return jsonify(ok=True, classes=["all", *classes])

    @app.get("/api/vision/runtime")
    def get_runtime_settings():
        return jsonify(ok=True, **state.runtime_settings.as_dict())

    @app.post("/api/vision/runtime")
    def update_runtime_settings():
        payload = request.get_json(silent=True) or {}
        infer_n = payload.get("infer_every_n_frames")
        if infer_n is not None:
            try:
                infer_n = max(1, int(infer_n))
            except (TypeError, ValueError):
                return jsonify(ok=False, error="invalid_infer_every_n_frames"), 400

        updated = state.runtime_settings.update(
            recognition_mode=payload.get("recognition_mode"),
            target_class=payload.get("target_class"),
            target_color=payload.get("target_color"),
            infer_every_n_frames=infer_n,
            draw_bbox=payload.get("draw_bbox"),
            draw_mask=payload.get("draw_mask"),
            draw_contour=payload.get("draw_contour"),
            draw_label=payload.get("draw_label"),
            retina_masks=payload.get("retina_masks"),
            conf_threshold=payload.get("conf_threshold"),
        )
        return jsonify(ok=True, **updated.__dict__)

    @app.get("/api/vision/metrics")
    def get_metrics():
        return jsonify(ok=True, **state.metrics.snapshot())

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
        if state.runtime.mode != "manual":
            return jsonify(ok=False, error="mode_must_be_manual"), 409
        state.runtime.target_angle = servo_service.set_angle(float(angle), force=True)
        return jsonify(ok=True, target_angle=state.runtime.target_angle)

    return app
