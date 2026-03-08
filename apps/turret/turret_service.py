"""Coordenação do serviço da turret."""

from __future__ import annotations

import copy
import threading

import yaml

from .servo_backend import FileServoBackend
from .state import SharedState
from .tracking import COLOR_PRESETS
from .video import run_tracking_loop
from .web import build_app


DEFAULT_CONFIG = {
    "camera": {"index": 0, "width": 424, "height": 240, "fps": 15},
    "tracking": {
        "color": "green",
        "area_min": 350,
        "kp": 18.0,
        "deadband": 0.10,
        "show_mask": True,
        "scan_on_target_loss": False,
        "scan_after_ms": 1500,
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
    "debug": {"frame_skip": 0, "verbose": False},
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
    cfg = deep_merge(DEFAULT_CONFIG, raw)
    if cfg["tracking"]["color"] not in COLOR_PRESETS:
        raise ValueError("tracking.color inválida")
    return cfg


def apply_overrides(cfg: dict, args):
    if args.color:
        cfg["tracking"]["color"] = args.color
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


def run_service(cfg: dict):
    state = SharedState(jpeg_quality=cfg["web"]["jpeg_quality"], show_mask=cfg["tracking"]["show_mask"])
    state.runtime.servo_enabled = cfg["servo"]["enabled"]
    state.runtime.color_name = cfg["tracking"]["color"]
    state.runtime.target_angle = float(cfg["servo"]["center_angle"])

    servo_backend = FileServoBackend(
        enabled=cfg["servo"]["enabled"],
        target_file=cfg["servo"]["target_file"],
        min_angle=cfg["servo"]["min_angle"],
        max_angle=cfg["servo"]["max_angle"],
        write_interval_ms=cfg["servo"]["write_interval_ms"],
        min_angle_step=cfg["servo"]["min_angle_step"],
    )

    tracking_thread = threading.Thread(target=run_tracking_loop, args=(cfg, state, servo_backend), daemon=True)
    tracking_thread.start()

    app = build_app(cfg, state, servo_backend)
    app.run(host=cfg["web"]["host"], port=cfg["web"]["port"], threaded=True)
