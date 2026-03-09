"""Flask app + UI para runtime de segmentação YOLO nano."""

from __future__ import annotations

import time

from flask import Flask, Response, jsonify, render_template_string, request

HTML = """
<!doctype html><html><head><meta charset="utf-8"/><title>KaiROS Vision</title>
<style>
body { background:#111; color:#eee; font-family:Arial,sans-serif; margin:16px; }
.row { display:flex; gap:16px; flex-wrap:wrap; }
.card { background:#1b1b1b; border-radius:12px; padding:12px; min-width:280px; }
img { width:100%; max-width:720px; border-radius:8px; }
button, select, input { margin:4px; padding:8px 12px; border-radius:8px; border:1px solid #333; background:#222; color:#eee; }
label { display:flex; align-items:center; justify-content:space-between; margin:8px 0; gap:10px; }
small.warn { color:#ff7e7e; font-weight:bold; }
</style></head>
<body>
<h2>KaiROS - YOLO Nano Segmentation</h2>
<div class="row">
  <div class="card"><h3>Video</h3><img src="/video_feed" /></div>
  <div class="card"><h3>Mask Stream</h3><img src="/mask_feed" /></div>
</div>
<div class="row">
  <div class="card">
    <h3>Controles em tempo real</h3>
    <label>Classe alvo<select id="targetClass"></select></label>
    <label>Inferência a cada N frames<input id="inferN" type="number" min="1" step="1"/></label>
    <label><span>Mostrar máscara</span><input id="drawMask" type="checkbox"/></label>
    <label><span>Mostrar bounding box</span><input id="drawBbox" type="checkbox"/></label>
    <label><span>Mostrar contorno</span><input id="drawContour" type="checkbox"/></label>
    <label><span>Mostrar label/conf</span><input id="drawLabel" type="checkbox"/></label>
    <button onclick="saveRuntime()">Aplicar runtime</button>
    <small id="feedback"></small>
  </div>
  <div class="card">
    <h3>Métricas</h3>
    <div>FPS frame: <b id="frameFps"></b></div>
    <div>Inferência média (ms): <b id="infAvg"></b></div>
    <div>Inferência/s: <b id="infFps"></b></div>
    <div>Classe alvo atual: <b id="targetNow"></b></div>
    <div>N atual: <b id="nNow"></b></div>
    <div>Status alvo: <b id="targetStatus"></b></div>
    <div>Confidence: <b id="conf"></b></div>
    <div>Área máscara: <b id="area"></b></div>
    <div>Estabilidade p95 (ms): <b id="p95"></b></div>
    <small id="targetWarn" class="warn"></small>
  </div>
</div>
<script>
async function jget(url){ const r = await fetch(url); return r.json(); }
async function jpost(url, body){ const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); return r.json(); }
function toast(msg, err=false){ feedback.textContent=msg; feedback.style.color = err?'#ff6b6b':'#8dff95'; setTimeout(()=>feedback.textContent='',2000); }
async function loadClasses(){
  const data = await jget('/api/vision/classes');
  targetClass.innerHTML='';
  data.classes.forEach((name)=>{ const o=document.createElement('option'); o.value=name; o.textContent=name; targetClass.appendChild(o);});
}
async function loadRuntime(){
  const d = await jget('/api/vision/runtime');
  targetClass.value=d.target_class; inferN.value=d.infer_every_n_frames;
  drawMask.checked=d.draw_mask; drawBbox.checked=d.draw_bbox; drawContour.checked=d.draw_contour; drawLabel.checked=d.draw_label;
}
async function saveRuntime(){
  const body={ target_class:targetClass.value, infer_every_n_frames:Number(inferN.value), draw_mask:drawMask.checked, draw_bbox:drawBbox.checked, draw_contour:drawContour.checked, draw_label:drawLabel.checked };
  const r = await jpost('/api/vision/runtime', body);
  toast(r.ok ? 'Runtime atualizado' : 'Falha ao atualizar', !r.ok);
}
async function refreshMetrics(){
  const m = await jget('/api/vision/metrics');
  frameFps.textContent=m.frame_fps.toFixed(2); infAvg.textContent=m.inference_avg_ms.toFixed(2); infFps.textContent=m.inference_fps.toFixed(2);
  targetNow.textContent=m.current_target_class; nNow.textContent=m.infer_every_n_frames; targetStatus.textContent=m.target_found?'encontrado':'perdido';
  conf.textContent=(m.class_confidence||0).toFixed(2); area.textContent=(m.mask_area||0).toFixed(1); p95.textContent=m.inference_p95_ms.toFixed(2);
  targetWarn.textContent=m.target_found ? '' : 'target not found';
}
setInterval(refreshMetrics, 600);
(async()=>{ await loadClasses(); await loadRuntime(); await refreshMetrics(); })();
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


def build_app(cfg: dict, state, servo_service, classes):
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
        metrics = state.metrics.snapshot()
        return jsonify(ok=True, mode=runtime.mode, target_angle=runtime.target_angle, modules={"vision": {"running": runtime.vision_running, "last_error": runtime.vision_last_error, "fps": runtime.vision_fps}}, metrics=metrics)

    @app.get("/api/vision/classes")
    def vision_classes():
        return jsonify(ok=True, classes=["all", *classes])

    @app.get("/api/vision/config")
    def vision_config():
        return jsonify(ok=True, config=cfg["detector"], render=cfg["render"], tracking=cfg["tracking"])

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
            target_class=payload.get("target_class"),
            infer_every_n_frames=infer_n,
            draw_bbox=payload.get("draw_bbox"),
            draw_mask=payload.get("draw_mask"),
            draw_contour=payload.get("draw_contour"),
            draw_label=payload.get("draw_label"),
            retina_masks=payload.get("retina_masks"),
            conf_threshold=payload.get("conf_threshold"),
        )
        return jsonify(ok=True, **updated.__dict__)

    @app.post("/api/vision/target")
    def update_target_class():
        payload = request.get_json(silent=True) or {}
        updated = state.runtime_settings.update(target_class=payload.get("target_class"))
        return jsonify(ok=True, target_class=updated.target_class)

    @app.post("/api/vision/infer_every_n_frames")
    def update_infer_n():
        payload = request.get_json(silent=True) or {}
        try:
            infer_n = int(payload.get("infer_every_n_frames"))
        except (TypeError, ValueError):
            return jsonify(ok=False, error="invalid_infer_every_n_frames"), 400
        updated = state.runtime_settings.update(infer_every_n_frames=max(1, infer_n))
        return jsonify(ok=True, infer_every_n_frames=updated.infer_every_n_frames)

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
