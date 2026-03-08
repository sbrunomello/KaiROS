#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x apps/turret/servo_daemon ]]; then
  echo "[ERRO] binário apps/turret/servo_daemon não encontrado. Rode ./scripts/build_servo_daemon.sh"
  exit 1
fi

exec ./apps/turret/servo_daemon
