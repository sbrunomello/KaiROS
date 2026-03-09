"""Entrypoint principal do KaiROS."""

from __future__ import annotations

import argparse

from .bot_service import apply_overrides, load_config, run_service


def parse_args():
    parser = argparse.ArgumentParser(description="KaiROS Bot Runtime V0")
    parser.add_argument("--config", default="apps/bot/config.yaml")
    parser.add_argument("--no-servo", action="store_true")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--fps", type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)
    apply_overrides(cfg, args)
    run_service(cfg)


if __name__ == "__main__":
    main()
