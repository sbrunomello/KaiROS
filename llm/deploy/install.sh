#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r llm/requirements.txt

if [[ ! -f llm/deploy/.env ]]; then
  cp llm/deploy/env.example llm/deploy/.env
fi

sudo cp llm/deploy/llm.service /etc/systemd/system/llm.service
sudo systemctl daemon-reload
sudo systemctl enable llm.service
sudo systemctl restart llm.service

echo "Instalação concluída. Configure llm/deploy/.env e verifique: systemctl status llm.service"
