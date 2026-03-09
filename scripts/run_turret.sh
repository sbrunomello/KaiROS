#!/usr/bin/env bash
set -euo pipefail

echo "[DEPRECATED] Este script será removido na próxima release. Use ./scripts/run_bot.sh" >&2
exec ./scripts/run_bot.sh "$@"
