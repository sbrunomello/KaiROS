#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo "[OK] venv criado em .venv"
echo "Ative com: source .venv/bin/activate"
