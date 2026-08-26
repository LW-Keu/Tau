#!/bin/bash
set -e

cd "$(dirname "$0")/.."

RUN_DIR="scripts/run"
mkdir -p "$RUN_DIR"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "error: $PYTHON_BIN not found; run 'uv venv && uv pip install -e .' first, or set PYTHON_BIN" >&2
  exit 1
fi

nohup "$PYTHON_BIN" -u -m tau_coding.taumain \
  --reflect tau_coding.reflect.autonomous \
  > "$RUN_DIR/autonomous.log" 2>&1 & echo $! > "$RUN_DIR/autonomous.pid"

echo "started autonomous, pid=$(cat "$RUN_DIR/autonomous.pid")"
echo "log: $(pwd)/$RUN_DIR/autonomous.log"
