#!/usr/bin/env bash
# subagent_review_template_audit.sh
# ----------------------------------------------------------
# 审计 subagent 评审产物 review.md 是否符合
# ../memories/autonomous_operation_sop/subagent_review_template.md §3 §4 的硬约束。
#
# 硬下限 (2026-06-18 L8 落盘后实测验证):
#   1) 文件存在且大小 >= 5120 bytes (5KB)
#   2) 7 个必备章节 (一/二/三/四/五/六/七)
#   3) JSON 评分数 ("name": 字段数) >= 待评审 [ ] TODO 数
# 额外:
#   - 检查 stdout.log 是否含 "覆盖"/"overwrit" 警告 (template §5 坑1)
#   - 退出码: 0=通过, 1=任意断言失败
#
# 用法:
#   bash subagent_review_template_audit.sh <TASK_NAME>
#   bash subagent_review_template_audit.sh <TASK_NAME> --strict  # JSON 数严格 >= TODO*1 (>=TODO_C, 留出余量)
#
# 入参:
#   $1 = TASK_NAME (对应 temp/$TASK_NAME/)
#   --strict = 可选, 启用严格模式 (JSON数必须 >= TODO数*1.5 取整)
#
# 环境依赖:
#   - bash >= 4 (使用 [[ ]])
#   - wc, grep, find (POSIX)
#   - TODO.txt 默认位于 cwd 或 temp/, 用 $TODO_FILE 覆盖
#
# 历史:
#   2026-08-31 R02_audit_script 落盘 (由 autonomous_operation_sop.md 委托)
#   来源: subagent_review_template.md §4 占位字符串 (2026-06-18 落)
# ----------------------------------------------------------

set -u

STRICT=0
for arg in "$@"; do
    case "$arg" in
        --strict) STRICT=1 ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            TASK="$arg"
            ;;
    esac
done

if [ -z "${TASK:-}" ]; then
    echo "用法: $0 <TASK_NAME> [--strict]" >&2
    exit 2
fi

# 路径解析: temp/$TASK/ 相对于 cwd
TASK_DIR="temp/$TASK"
REVIEW="$TASK_DIR/review.md"
STDOUT="$TASK_DIR/stdout.log"
TODO_FILE="${TODO_FILE:-$TASK_DIR/TODO.txt}"
# 若任务目录没 TODO.txt, 回退到 cwd/TODO.txt (兼容旧 subagent 产物)
[ ! -f "$TODO_FILE" ] && TODO_FILE="TODO.txt"

# 颜色 (无 TTY 时禁用)
if [ -t 1 ]; then
    RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; NC=$'\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; NC=''
fi

fail() {
    echo "${RED}❌ $1${NC}" >&2
    exit 1
}

pass() {
    echo "${GREEN}✅ $1${NC}"
}

warn() {
    echo "${YELLOW}⚠️  $1${NC}"
}

# --- 断言 1: 文件存在 + size >= 5KB ---
[ -f "$REVIEW" ] || fail "review.md 不存在: $REVIEW"
SIZE=$(wc -c < "$REVIEW" | tr -d ' ')
[ "$SIZE" -ge 5120 ] || fail "产物 < 5KB ($SIZE B, 需 >= 5120)"
pass "断言1: 产物大小 OK ($SIZE B)"

# --- 断言 2: 7 个必备章节 ---
MISSING_SEC=""
for sec in "一、" "二、" "三、" "四、" "五、" "六、" "七、"; do
    if ! grep -q "^## $sec" "$REVIEW"; then
        MISSING_SEC="$MISSING_SEC $sec"
    fi
done
if [ -n "$MISSING_SEC" ]; then
    fail "缺节:${MISSING_SEC}"
fi
pass "断言2: 7 个章节齐全"

# --- 断言 3: JSON 评分数 >= TODO 数 ---
TODO_C=$(grep -c "^\\[ \\]" "$TODO_FILE" 2>/dev/null || echo 0)
JSON_C=$(grep -c '"name":' "$REVIEW" 2>/dev/null || echo 0)

if [ "$STRICT" -eq 1 ]; then
    NEEDED=$(( (TODO_C * 3 + 1) / 2 ))  # 1.5x
else
    NEEDED=$TODO_C
fi

if [ "$JSON_C" -lt "$NEEDED" ]; then
    fail "评分 JSON 不足: review=$JSON_C, TODO=$TODO_C, 需要>=$NEEDED (--strict=${STRICT})"
fi
pass "断言3: JSON 评分数 OK ($JSON_C >= $NEEDED, TODO=$TODO_C)"

# --- 额外: stdout.log 覆盖检查 (template §5 坑1) ---
if [ -f "$STDOUT" ]; then
    if grep -qiE "output.*覆盖|overwrit|replaced" "$STDOUT"; then
        warn "stdout.log 含覆盖警告 — 可能是 subagent output.txt 被对话流覆盖 (template §5 坑1)"
        warn "  建议: 复核 review.md 是否真为 subagent 产物 (而不是对话流 dump)"
    fi
fi

# --- 额外: 行数下限提示 ---
LINES=$(wc -l < "$REVIEW" | tr -d ' ')
if [ "$LINES" -lt 200 ]; then
    warn "行数 $LINES < 200 (template §3 建议下限), 但 size 断言已通过"
fi

echo ""
echo "${GREEN}✅ 验收通过${NC}: $REVIEW ($SIZE B, $LINES 行, $JSON_C 评分)"
exit 0