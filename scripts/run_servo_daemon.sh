#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x apps/bot/servo_daemon ]]; then
  echo "[ERRO] binário apps/bot/servo_daemon não encontrado. Rode ./scripts/build_servo_daemon.sh"
  exit 1
fi

exec ./apps/bot/servo_daemon
