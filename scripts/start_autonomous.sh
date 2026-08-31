#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_DIR="scripts/run"
mkdir -p "$RUN_DIR"

PYTHON_BIN=".venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "错误：未找到 Python 虚拟环境：$PYTHON_BIN"
  echo "请先在项目根目录执行：python3 -m venv .venv"
  echo "然后安装项目依赖。"
  exit 1
fi

nohup "$PYTHON_BIN" -u -m tau_coding.taumain \
  --reflect tau_coding.reflect.autonomous \
  > "$RUN_DIR/autonomous.log" 2>&1 &

echo $! > "$RUN_DIR/autonomous.pid"

sleep 1

if kill -0 "$(cat "$RUN_DIR/autonomous.pid")" 2>/dev/null; then
  echo "started autonomous, pid=$(cat "$RUN_DIR/autonomous.pid")"
  echo "log: $(pwd)/$RUN_DIR/autonomous.log"
else
  echo "启动失败；请检查日志：$(pwd)/$RUN_DIR/autonomous.log"
  cat "$RUN_DIR/autonomous.log"
  exit 1
fi