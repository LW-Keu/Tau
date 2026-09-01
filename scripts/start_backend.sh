#!/usr/bin/env bash
#
# API 服务管理脚本
#
# 用法：
#   ./scripts/api.sh start [server.py 参数...]
#   ./scripts/api.sh stop
#   ./scripts/api.sh restart [server.py 参数...]
#   ./scripts/api.sh status
#   ./scripts/api.sh logs
#
# 示例：
#   ./scripts/api.sh start --host 0.0.0.0 --port 8000
#   ./scripts/api.sh logs
#
# 可选环境变量：
#   UV_BIN=uv
#   PYTHON_BIN=python3
#   API_SERVER=apps/api/server.py
#   LOG_FILE=/absolute/or/relative/path/api.log
#   PID_FILE=/absolute/or/relative/path/api.pid
#   STOP_TIMEOUT=15
#

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

UV_BIN="${UV_BIN:-uv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
API_SERVER="${API_SERVER:-apps/api/server.py}"

LOG_DIR="${LOG_DIR:-${PROJECT_ROOT}/logs}"
RUN_DIR="${RUN_DIR:-${PROJECT_ROOT}/run}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/api.log}"
PID_FILE="${PID_FILE:-${RUN_DIR}/api.pid}"
STOP_TIMEOUT="${STOP_TIMEOUT:-15}"

readonly SCRIPT_DIR PROJECT_ROOT UV_BIN PYTHON_BIN API_SERVER
readonly LOG_DIR RUN_DIR LOG_FILE PID_FILE STOP_TIMEOUT

usage() {
  cat <<EOF
用法：
  $(basename "$0") <start|stop|restart|status|logs> [server.py 参数...]

命令：
  start       后台启动 API 服务，并写入 PID 和日志
  stop        优雅停止 API 服务
  restart     重启 API 服务
  status      查看 API 服务运行状态
  logs        持续查看 API 日志

示例：
  $(basename "$0") start --host 0.0.0.0 --port 8000
  $(basename "$0") stop
  $(basename "$0") status
  $(basename "$0") logs
EOF
}

ensure_dependencies() {
  command -v "$UV_BIN" >/dev/null 2>&1 || {
    echo "错误：未找到 uv 命令：${UV_BIN}" >&2
    echo "请安装 uv，或通过 UV_BIN 指定其可执行文件路径。" >&2
    exit 127
  }

  if [[ ! -f "${PROJECT_ROOT}/${API_SERVER}" ]]; then
    echo "错误：找不到 API 服务入口文件：${PROJECT_ROOT}/${API_SERVER}" >&2
    exit 1
  fi
}

ensure_directories() {
  mkdir -p "$LOG_DIR" "$RUN_DIR"
  touch "$LOG_FILE"
}

read_pid() {
  [[ -f "$PID_FILE" ]] || return 1

  local pid
  pid="$(tr -d '[:space:]' < "$PID_FILE")"

  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "$pid"
}

is_running() {
  local pid

  pid="$(read_pid)" || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

remove_stale_pid_file() {
  if [[ -f "$PID_FILE" ]] && ! is_running; then
    echo "检测到过期 PID 文件，正在删除：${PID_FILE}"
    rm -f "$PID_FILE"
  fi
}

start() {
  ensure_dependencies
  ensure_directories
  remove_stale_pid_file

  if is_running; then
    local pid
    pid="$(read_pid)"
    echo "API 服务已在运行中，PID：${pid}"
    echo "日志文件：${LOG_FILE}"
    return 0
  fi

  echo "正在启动 API 服务..."
  echo "项目目录：${PROJECT_ROOT}"
  echo "服务入口：${API_SERVER}"
  echo "日志文件：${LOG_FILE}"
  echo "PID 文件：${PID_FILE}"

  {
    echo
    echo "================================================================"
    echo "[$(date '+%Y-%m-%d %H:%M:%S %z')] Starting API service"
    echo "Command: ${UV_BIN} run ${PYTHON_BIN} ${API_SERVER} $*"
    echo "================================================================"
  } >> "$LOG_FILE"

  cd "$PROJECT_ROOT"

  # nohup：脱离终端，终端关闭后服务继续运行。
  # "$@"：将 start 后面的参数完整转发给 server.py。
  nohup "$UV_BIN" run "$PYTHON_BIN" "$API_SERVER" "$@" \
    >> "$LOG_FILE" 2>&1 < /dev/null &

  local pid=$!
  printf '%s\n' "$pid" > "$PID_FILE"

  # 给进程短暂时间启动；若立即退出，报告失败并清理 PID 文件。
  sleep 1

  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "API 服务已启动，PID：${pid}"
    echo "查看日志：tail -f ${LOG_FILE}"
  else
    echo "错误：API 服务启动失败。请检查日志：${LOG_FILE}" >&2
    rm -f "$PID_FILE"
    return 1
  fi
}

stop() {
  remove_stale_pid_file

  if ! is_running; then
    echo "API 服务未运行。"
    return 0
  fi

  local pid
  pid="$(read_pid)"

  echo "正在停止 API 服务，PID：${pid}..."
  kill -TERM "$pid"

  local elapsed=0
  while kill -0 "$pid" >/dev/null 2>&1; do
    if (( elapsed >= STOP_TIMEOUT )); then
      echo "服务在 ${STOP_TIMEOUT} 秒内未停止，正在强制结束..."
      kill -KILL "$pid" >/dev/null 2>&1 || true
      break
    fi

    sleep 1
    ((elapsed += 1))
  done

  rm -f "$PID_FILE"
  echo "API 服务已停止。"
}

status() {
  remove_stale_pid_file

  if is_running; then
    local pid
    pid="$(read_pid)"
    echo "API 服务正在运行，PID：${pid}"
    echo "日志文件：${LOG_FILE}"
    echo "PID 文件：${PID_FILE}"
  else
    echo "API 服务未运行。"
    return 1
  fi
}

logs() {
  ensure_directories
  echo "持续输出日志：${LOG_FILE}"
  exec tail -n 100 -f "$LOG_FILE"
}

restart() {
  stop
  start "$@"
}

main() {
  local command="${1:-}"

  case "$command" in
    start)
      shift
      start "$@"
      ;;
    stop)
      stop
      ;;
    restart)
      shift
      restart "$@"
      ;;
    status)
      status
      ;;
    logs)
      logs
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "错误：未知命令：${command}" >&2
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"