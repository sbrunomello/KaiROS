#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x .venv/bin/python ]]; then
  echo "[ERRO] .venv ausente. Rode ./scripts/setup_venv.sh"
  exit 1
fi

exec ./.venv/bin/python -m apps.turret.turret_web "$@"
