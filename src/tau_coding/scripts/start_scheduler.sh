#!/bin/bash
set -e

# ======================== 配置区 ========================
PORT="${SCHEDULER_PORT:-45762}"       # scheduler 实例检测端口（默认 45762）
LOG_FILE="scheduler.log"
PID_FILE="scheduler.pid"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MODULE="tau_coding.taumain"
REFLECT_MODULE="tau_coding.reflect.scheduler"
# ========================================================

cd "$(dirname "$0")"
WORK_DIR="$(pwd)"

# ---------- 颜色 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
header(){ echo -e "${CYAN}[====]${NC}  $*"; }

# ---------- 端口检测 ----------
check_port() {
    local port="$1"
    if command -v lsof &>/dev/null; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null \
            | awk 'NR > 1 {print "users:((\"" $1 "\",pid=" $2 "))"}' || true
    elif command -v ss &>/dev/null; then
        ss -tulnp 2>/dev/null | grep ":${port} " || true
    fi
}

extract_pids() {
    printf '%s\n' "$1" | awk '{
        users = index($0, "users:(")
        if (!users) next
        rest = substr($0, users)
        while (match(rest, /pid=[0-9]+/)) {
            print substr(rest, RSTART + 4, RLENGTH - 4)
            rest = substr(rest, RSTART + RLENGTH)
        }
    }' | sort -u
}

is_verified_scheduler_pid() {
    local pid="$1" args
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    (( pid > 1 )) || return 1
    [ "$pid" != "$$" ] && [ "$pid" != "$PPID" ] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    args=$(ps -p "$pid" -o args= 2>/dev/null) || return 1
    [[ "$args" == *"${MODULE}"* && "$args" == *"${REFLECT_MODULE}"* ]]
}

get_proc_detail() {
    local pid="$1"
    ps -p "$pid" -o pid,user,%cpu,%mem,lstart,args --no-headers 2>/dev/null \
        || echo "（无法获取 PID=${pid} 的进程信息）"
}

terminate_verified_scheduler_pid() {
    local pid="$1"
    info "正在终止进程 PID=${pid} ..."
    if ! is_verified_scheduler_pid "$pid"; then
        warn "进程 PID=${pid} 身份已变化，停止发送信号。"
        return 0
    fi
    kill -15 "$pid" 2>/dev/null || true
    for i in 1 2 3; do
        sleep 1
        if ! kill -0 "$pid" 2>/dev/null; then break; fi
    done
    if kill -0 "$pid" 2>/dev/null; then
        warn "进程 PID=${pid} 未响应 SIGTERM，准备发送 SIGKILL ..."
        if ! is_verified_scheduler_pid "$pid"; then
            warn "进程 PID=${pid} 身份已变化，停止发送信号。"
            return 0
        fi
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    if kill -0 "$pid" 2>/dev/null; then
        error "无法终止进程 PID=${pid}，请手动处理。"
        return 1
    fi
    info "进程 PID=${pid} 已终止。"
}

# ---------- kv 输出（printf 固定宽度对齐）----------
KV_MAX_LABEL=22
print_kv() {
    local label="$1" value="$2"
    printf "  %-${KV_MAX_LABEL}s : %s\n" "$label" "$value"
}

print_separator() {
    printf "  +-%s-+-%s-+\n" \
        "$(printf '%0.s-' $(seq 1 $KV_MAX_LABEL))" \
        "$(printf '%0.s-' $(seq 1 36))"
}

# ========================================================
#                    主流程
# ========================================================

header "Scheduler 启动脚本"
info "工作目录 : ${WORK_DIR}"
info "检查端口 : ${PORT}"
info "Python   : ${PYTHON_BIN}"
echo ""

# ---------- Step 1: 端口检测 ----------
CONFLICT_INFO=$(check_port "$PORT")

if [ -n "$CONFLICT_INFO" ]; then
    warn "端口 ${PORT} 已被以下进程占用："
    echo ""
    echo "  ────────────────────────────────────────────────────────────"
    printf "  %-8s %-10s %-6s %-6s %-25s %s\n" "PID" "USER" "CPU%" "MEM%" "START" "COMMAND"
    echo "  ────────────────────────────────────────────────────────────"

    PIDS=$(extract_pids "$CONFLICT_INFO")
    VERIFIED_PIDS=""
    for pid in $PIDS; do
        if is_verified_scheduler_pid "$pid"; then
            VERIFIED_PIDS="${VERIFIED_PIDS} ${pid}"
            get_proc_detail "$pid"
        else
            warn "拒绝未验证的进程 PID=${pid}"
        fi
    done
    PIDS="$VERIFIED_PIDS"
    if [ -z "${PIDS// }" ]; then
        error "未找到可验证的 scheduler 进程，拒绝发送信号。"
        exit 1
    fi
    echo "  ────────────────────────────────────────────────────────────"
    echo ""

    # ---------- Step 2: 询问用户 ----------
    printf "是否需要 kill 掉占用端口的进程并启动 scheduler？[yes/no] "
    read -r USER_REPLY

    if [ "$USER_REPLY" = "yes" ] || [ "$USER_REPLY" = "y" ]; then
        echo ""
        for pid in $PIDS; do
            terminate_verified_scheduler_pid "$pid" || exit 1
        done

        # ---------- Step 3: 二次确认 ----------
        sleep 1
        REMAIN=$(check_port "$PORT")
        if [ -n "$REMAIN" ]; then
            error "端口 ${PORT} 仍被占用，放弃启动："
            echo "$REMAIN"
            exit 1
        fi
        info "端口 ${PORT} 已释放。"
        echo ""
    else
        info "用户选择取消，脚本退出。"
        exit 0
    fi
else
    info "端口 ${PORT} 空闲，无需清理。"
    echo ""
fi

# ---------- Step 4: 启动 scheduler ----------
header "启动 Scheduler"

START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

nohup "${PYTHON_BIN}" -u -m "${MODULE}" --reflect "${REFLECT_MODULE}" > "${LOG_FILE}" 2>&1 &
SCHEDULER_PID=$!
echo "$SCHEDULER_PID" > "${PID_FILE}"

sleep 2

# ---------- Step 5: 启动详情 ----------
echo ""
print_separator
print_kv "Scheduler 启动详情" ""
print_separator
if kill -0 "$SCHEDULER_PID" 2>/dev/null; then
    print_kv "状态" "✅ 运行中"
else
    print_kv "状态" "❌ 已退出"
fi
print_kv "PID" "$SCHEDULER_PID"
print_kv "启动时间" "$START_TIME"
print_kv "Python 解释器" "${PYTHON_BIN}"
print_kv "模块" "${MODULE}"
print_kv "Reflect 参数" "${REFLECT_MODULE}"
print_kv "工作目录" "${WORK_DIR}"
print_kv "监听端口" "${PORT}"
print_kv "日志文件" "${WORK_DIR}/${LOG_FILE}"
print_kv "PID 文件" "${WORK_DIR}/${PID_FILE}"
print_separator
echo ""
print_kv "进程详情 (ps)" ""
echo "  $(ps -p "$SCHEDULER_PID" -o pid,ppid,user,%cpu,%mem,etime,args --no-headers 2>/dev/null || echo '(进程已退出)')"
echo ""
print_kv "日志预览 (最近 10 行)" ""
echo "  ────────────────────────────────────────────────────────────"
if [ -f "${LOG_FILE}" ]; then
    tail -n 10 "${LOG_FILE}" 2>/dev/null | while IFS= read -r line; do
        echo "  ${line}"
    done
else
    echo "  (暂无日志)"
fi
echo "  ────────────────────────────────────────────────────────────"
echo ""

# ---------- Step 6: 最终状态 ----------
if kill -0 "$SCHEDULER_PID" 2>/dev/null; then
    info "Scheduler 启动成功！PID=${SCHEDULER_PID}"
    info "查看实时日志: tail -f ${WORK_DIR}/${LOG_FILE}"
    info "停止服务:     kill ${SCHEDULER_PID}"
else
    error "Scheduler 进程已退出，请检查日志: ${WORK_DIR}/${LOG_FILE}"
    exit 1
fi
