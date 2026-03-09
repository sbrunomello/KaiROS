"""Coordenação do serviço do bot."""

from __future__ import annotations

import copy
import threading

import yaml

from .runtime.settings import RuntimeSettingsStore, VisionRuntimeSettings
from .servo_backend import FileServoBackend
from .servo_service import ServoService
from .state import SharedState
from .vision_service import VisionService
from .web import build_app

DEFAULT_CONFIG = {
    "camera": {"index": 0, "width": 424, "height": 240, "fps": 15},
    "tracking": {
        "scan_on_target_loss": False,
        "scan_after_ms": 1500,
        "ema_alpha": 0.35,
        "tracking_timeout_ms": 1200,
        "kp": 6.0,
        "deadband": 0.08,
        "area_min": 350,
    },
    "detector": {
        "enabled": True,
        "model_path": "yolo26n-seg.pt",
        "conf_threshold": 0.25,
        "iou_threshold": 0.45,
        "imgsz": 640,
        "retina_masks": True,
        "infer_every_n_frames_default": 1,
        "target_class_default": "all",
        "device": None,
    },
    "render": {
        "overlay_alpha": 0.45,
        "draw_bbox_default": False,
        "draw_mask_default": True,
        "draw_contour_default": True,
        "draw_label_default": True,
    },
    "servo": {
        "enabled": True,
        "center_angle": 90,
        "min_angle": 60,
        "max_angle": 120,
        "write_interval_ms": 80,
        "min_angle_step": 1.0,
        "target_file": "/tmp/kairos_servo_target",
    },
    "web": {"host": "0.0.0.0", "port": 8080, "jpeg_quality": 55, "stream_sleep_ms": 50},
    "debug": {"verbose": False},
}


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fp:
        raw = yaml.safe_load(fp) or {}
    return deep_merge(DEFAULT_CONFIG, raw)


def apply_overrides(cfg: dict, args):
    if args.no_servo:
        cfg["servo"]["enabled"] = False
    if args.host:
        cfg["web"]["host"] = args.host
    if args.port:
        cfg["web"]["port"] = args.port
    if args.width:
        cfg["camera"]["width"] = args.width
    if args.height:
        cfg["camera"]["height"] = args.height
    if args.fps:
        cfg["camera"]["fps"] = args.fps
    if getattr(args, "no_detector", False):
        cfg["detector"]["enabled"] = False


def run_service(cfg: dict):
    runtime_settings = RuntimeSettingsStore(
        VisionRuntimeSettings(
            recognition_mode="yolo" if cfg["detector"].get("enabled", True) else "color",
            target_class=cfg["detector"]["target_class_default"],
            target_color=cfg.get("color_tracking", {}).get("target_color_default", "blue"),
            infer_every_n_frames=cfg["detector"]["infer_every_n_frames_default"],
            draw_bbox=cfg["render"]["draw_bbox_default"],
            draw_mask=cfg["render"]["draw_mask_default"],
            draw_contour=cfg["render"]["draw_contour_default"],
            draw_label=cfg["render"]["draw_label_default"],
            retina_masks=cfg["detector"]["retina_masks"],
            conf_threshold=cfg["detector"]["conf_threshold"],
        )
    )
    state = SharedState(jpeg_quality=cfg["web"]["jpeg_quality"], show_mask=True, runtime_settings=runtime_settings)
    state.runtime.servo_enabled = cfg["servo"]["enabled"]
    state.runtime.desired_camera_index = int(cfg["camera"]["index"])
    state.runtime.active_camera_index = None
    state.runtime.target_angle = float(cfg["servo"]["center_angle"])

    servo_backend = FileServoBackend(
        enabled=cfg["servo"]["enabled"],
        target_file=cfg["servo"]["target_file"],
        min_angle=cfg["servo"]["min_angle"],
        max_angle=cfg["servo"]["max_angle"],
        write_interval_ms=cfg["servo"]["write_interval_ms"],
        min_angle_step=cfg["servo"]["min_angle_step"],
    )
    servo_service = ServoService(servo_backend)
    # Sempre iniciamos o serviço de visão para manter o stream da webcam ativo,
    # mesmo quando o detector YOLO estiver desabilitado (fallback por cor).
    vision_service = VisionService(cfg, state, servo_service)
    model_classes = vision_service.model_classes
    recognition_modes = vision_service.recognition_modes
    color_presets = vision_service.color_presets
    tracking_thread = threading.Thread(target=vision_service.run, daemon=True)
    tracking_thread.start()

    app = build_app(
        cfg,
        state,
        servo_service,
        classes=model_classes,
        recognition_modes=recognition_modes,
        color_presets=color_presets,
    )
    app.run(host=cfg["web"]["host"], port=cfg["web"]["port"], threaded=True)
