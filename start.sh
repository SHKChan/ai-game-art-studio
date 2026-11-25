#!/usr/bin/env bash
# AI Game Art Studio - Linux/macOS launcher.  Usage: ./start.sh [--port 8870] [--workspace DIR] [--comfy URL]
set -euo pipefail
cd "$(dirname "$0")"
PORT=8870
while [[ $# -gt 0 ]]; do case "$1" in
  --port) PORT="$2"; shift 2;; --workspace) export ARTSTUDIO_WORKSPACE="$2"; shift 2;;
  --comfy) export COMFYUI_URL="$2"; shift 2;; *) echo "unknown option $1"; exit 1;; esac; done
if [[ -f .env ]]; then set -a; . ./.env; set +a; fi
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8   # UTF-8 mode regardless of locale
PY=${PYTHON:-python3}
if [[ ! -x .venv/bin/python ]]; then
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python -m artstudio serve --port "$PORT"
