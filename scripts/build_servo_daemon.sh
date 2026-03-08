#!/usr/bin/env bash
set -euo pipefail

gcc apps/turret/servo_daemon.c -o apps/turret/servo_daemon -lwiringPi -lpthread

echo "[OK] binário gerado em apps/turret/servo_daemon"
