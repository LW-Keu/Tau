#!/bin/bash
set -e

PID_FILE="scripts/run/autonomous.pid"

cd "$(dirname "$0")/.."

if [ -f "$PID_FILE" ]; then
  kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE"
  echo "autonomous stopped"
else
  echo "$PID_FILE not found"
fi
