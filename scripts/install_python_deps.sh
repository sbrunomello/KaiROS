#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x .venv/bin/pip ]]; then
  echo "[ERRO] .venv não encontrado. Rode ./scripts/setup_venv.sh primeiro."
  exit 1
fi

./.venv/bin/pip install -r requirements.txt
