"""Entrypoint principal do KaiROS."""

from __future__ import annotations

import argparse

from .runtime.preflight import PreflightError, run_binary_dependency_preflight


def parse_args():
    parser = argparse.ArgumentParser(description="KaiROS Bot Runtime V0")
    parser.add_argument("--config", default="apps/bot/config.yaml")
    parser.add_argument("--no-servo", action="store_true")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--fps", type=int)
    parser.add_argument("--no-detector", action="store_true", help="inicia sem carregar YOLO/torch")
    return parser.parse_args()


def main():
    args = parse_args()

    # Import tardio para garantir que falhas de binários nativos sejam reportadas
    # de forma amigável no preflight em vez de derrubar o processo com SIGILL.
    from .bot_service import apply_overrides, load_config, run_service

    cfg = load_config(args.config)
    apply_overrides(cfg, args)

    try:
        run_binary_dependency_preflight(detector_enabled=cfg["detector"].get("enabled", True))
    except PreflightError as exc:
        raise SystemExit(f"[KAIROS PRECHECK] {exc}") from exc

    run_service(cfg)


if __name__ == "__main__":
    main()
