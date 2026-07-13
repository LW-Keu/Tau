#!/usr/bin/env python3
"""
active_window.py — 查询当前前台活动应用 (用例 4 / l3_capability_inventory §8.10)

用法:
    python3 active_window.py                   # 输出 JSON
    python3 active_window.py --format text     # 输出 人类可读
    python3 active_window.py --format markdown # 输出 markdown 表格

依赖:
    - macOS (osascript)
    - System Events 需在"辅助功能"中授权 Terminal / Python.app

退出码:
    0  成功
    1  AppleScript 执行失败（stderr 已输出）
    2  非 macOS
"""
import json
import platform
import subprocess
import sys

# AppleScript: 同时取 app 名 + 窗口标题 + 进程 PID
_OSASCRIPT = """
tell application "System Events"
  set procApp to first application process whose frontmost is true
  set appName to name of procApp
  set appPid to unix id of procApp
  try
    set winTitle to name of front window of procApp
  on error
    set winTitle to ""
  end try
end tell
return appName & "|" & winTitle & "|" & appPid
"""


def query_frontmost() -> dict:
    """调用 osascript, 返回 dict. 失败抛 RuntimeError."""
    try:
        result = subprocess.run(
            ["osascript", "-e", _OSASCRIPT],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        raise RuntimeError("osascript not found (need macOS)")
    except subprocess.TimeoutExpired:
        raise RuntimeError("osascript timeout (5s)")

    if result.returncode != 0:
        err = (result.stderr or "").strip() or f"exit={result.returncode}"
        raise RuntimeError(f"AppleScript failed: {err}")

    raw = (result.stdout or "").strip()
    if "|" not in raw:
        raise RuntimeError(f"unexpected output: {raw!r}")

    parts = raw.split("|", 2)
    if len(parts) != 3:
        raise RuntimeError(f"parse error: {raw!r}")

    app_name, win_title, pid_str = parts
    try:
        pid = int(pid_str)
    except ValueError:
        raise RuntimeError(f"pid parse error: {pid_str!r}")

    return {
        "app_name": app_name,
        "window_title": win_title,
        "pid": pid,
    }


def to_text(d: dict) -> str:
    return (
        f"App: {d['app_name']}\n"
        f"Window: {d['window_title'] or '(无窗口)'}\n"
        f"PID: {d['pid']}"
    )


def to_markdown(d: dict) -> str:
    return (
        "| 字段 | 值 |\n|---|---|\n"
        f"| App | {d['app_name']} |\n"
        f"| Window | {d['window_title'] or '_(无窗口)_'} |\n"
        f"| PID | {d['pid']} |"
    )


def main() -> int:
    if platform.system() != "Darwin":
        print("ERROR: 需要 macOS 才能用 System Events", file=sys.stderr)
        return 2

    fmt = "json"
    args = sys.argv[1:]
    if "--format" in args:
        i = args.index("--format")
        if i + 1 < len(args):
            fmt = args[i + 1]

    try:
        data = query_frontmost()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if fmt == "text":
        print(to_text(data))
    elif fmt == "markdown":
        print(to_markdown(data))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
