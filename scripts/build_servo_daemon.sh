#!/usr/bin/env bash
set -euo pipefail

gcc apps/bot/servo_daemon.c -o apps/bot/servo_daemon -lwiringPi -lpthread

echo "[OK] binário gerado em apps/bot/servo_daemon"
