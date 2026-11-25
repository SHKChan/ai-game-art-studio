#!/usr/bin/env bash
# Launch the original Pixel Atelier workbench in Python UTF-8 mode.
set -euo pipefail
cd "$(dirname "$0")/../upstream/pixel-atelier"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
PY=../../.venv/bin/python; [[ -x $PY ]] || PY=python3
exec "$PY" -X utf8 bridge/server.py --port "${1:-8898}"
