#!/bin/bash
set -e

cd "$(dirname "$0")/.."

RUN_DIR="scripts/run"
mkdir -p "$RUN_DIR"

nohup python3 -u -m tau_coding.taumain \
  --reflect tau_coding.reflect.autonomous \
  > "$RUN_DIR/autonomous.log" 2>&1 & echo $! > "$RUN_DIR/autonomous.pid"

echo "started autonomous, pid=$(cat "$RUN_DIR/autonomous.pid")"
echo "log: $(pwd)/$RUN_DIR/autonomous.log"
