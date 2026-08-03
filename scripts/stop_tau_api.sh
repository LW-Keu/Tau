#!/bin/bash
set -e

PORT="${TAU_API_PORT:-8644}"
PID_FILE="scripts/run/tau_api.pid"

cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

error() { echo -e "${RED}[ERROR]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }

is_tau_api_pid() {
    local pid="$1" args
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    args=$(ps -p "$pid" -o args= 2>/dev/null) || return 1
    [[ "$args" == *"tau"* && "$args" == *"api"* ]]
}

terminate() {
    local pid="$1"
    info "正在终止 PID=${pid} ..."
    kill -15 "$pid" 2>/dev/null || true
    for i in 1 2 3; do
        sleep 1
        if ! kill -0 "$pid" 2>/dev/null; then
            info "PID=${pid} 已终止。"
            return 0
        fi
    done
    if kill -0 "$pid" 2>/dev/null; then
        warn "未响应 SIGTERM，发送 SIGKILL ..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    if kill -0 "$pid" 2>/dev/null; then
        error "无法终止 PID=${pid}，请手动处理。"
        return 1
    fi
    info "PID=${pid} 已终止。"
}

# --- 优先用 PID 文件，其次扫端口 ---
FOUND_PID=""

if [ -f "$PID_FILE" ] && read -r pid < "$PID_FILE" && is_tau_api_pid "$pid"; then
    FOUND_PID="$pid"
fi

if [ -z "$FOUND_PID" ]; then
    FOUND_PID=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -n "$FOUND_PID" ] && ! is_tau_api_pid "$FOUND_PID"; then
        warn "端口 ${PORT} 上的进程不是 tau api，拒绝终止。"
        exit 1
    fi
fi

if [ -z "$FOUND_PID" ]; then
    info "tau api 未在运行（端口 ${PORT} 空闲）。"
    exit 0
fi

terminate "$FOUND_PID"
rm -f "$PID_FILE"
info "tau api 已停止。"
