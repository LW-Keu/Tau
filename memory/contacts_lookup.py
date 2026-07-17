#!/usr/bin/env python3
"""
contacts_lookup.py — Contacts 模糊查询 (用例 6 / l3_capability_inventory §8.10)

用法:
    python3 contacts_lookup.py 张           # 模糊搜索名字含"张"的所有联系人
    python3 contacts_lookup.py 张三 --format csv     # 明确输出格式
    python3 contacts_lookup.py 张三 --format markdown # 默认 markdown 表格

依赖:
    - macOS (Contacts.app, osascript)
    - 需在"通讯录"授权 (System Events -> Contacts)

退出码:
    0  成功（无论找到几条）
    1  AppleScript 失败
    2  非 macOS
    3  Contacts 不可用（剪贴板或权限拒绝）
"""
import argparse
import platform
import subprocess
import sys

# AppleScript: 搜索名字含 query 的人, 输出 name|phone|email 每条一行
# 注意: Contacts 中的 phone/email 字段可能不存在，用 "-" 占位
_OSASCRIPT = r"""
on safe_value(v)
  if v is missing value then return "-"
  return v as text
end safe_value

on run
  set q to "{QUERY}"
  set outLines to {{}}
  tell application "Contacts"
    set matches to (every person whose name contains q)
    repeat with p in matches
      set n to name of p
      set ph to "-"
      set em to "-"
      try
        set ph to safe_value(value of phone 1 of p)
      end try
      try
        set em to safe_value(value of email 1 of p)
      end try
      set end of outLines to (n & "|" & ph & "|" & em)
    end repeat
  end tell
  set AppleScript's text item delimiters to linefeed
  return outLines as text
end run
"""


def build_script(query: str) -> str:
    # AppleScript string 转义: 反斜杠与双引号
    esc = query.replace("\\", "\\\\").replace('"', '\\"')
    return _OSASCRIPT.replace("{QUERY}", esc)


def query_contacts(query: str) -> list:
    """返回 [(name, phone, email), ...], 失败抛 RuntimeError."""
    script = build_script(query)
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise RuntimeError("osascript not found (need macOS)")
    except subprocess.TimeoutExpired:
        raise RuntimeError("osascript timeout (10s)")

    if result.returncode != 0:
        err = (result.stderr or "").strip()
        # 常见: 权限被拒 / Contacts 未设默认账户 / 没找到人
        if not err:
            err = f"exit={result.returncode}"
        raise RuntimeError(f"AppleScript failed: {err}")

    out = (result.stdout or "").strip()
    rows = []
    if out:
        for line in out.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                rows.append(tuple(parts))
            else:
                rows.append((line, "-", "-"))
    return rows


def to_markdown(rows: list) -> str:
    if not rows:
        return "_未找到匹配联系人_"
    lines = ["| 姓名 | 电话 | 邮箱 |", "|---|---|---|"]
    for n, p, e in rows:
        lines.append(f"| {n} | {p} | {e} |")
    return "\n".join(lines)


def to_csv(rows: list) -> str:
    if not rows:
        return "name,phone,email\n"
    out = ["name,phone,email"]
    for n, p, e in rows:
        out.append(f'"{n}","{p}","{e}"')
    return "\n".join(out)


def main() -> int:
    if platform.system() != "Darwin":
        print("ERROR: 需要 macOS 才能访问 Contacts", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(description="Contacts 模糊查询")
    parser.add_argument("query", help="搜索关键词（中文/英文均可）")
    parser.add_argument(
        "--format",
        choices=["markdown", "csv", "tsv"],
        default="markdown",
        help="输出格式 (默认 markdown)",
    )
    args = parser.parse_args()

    try:
        rows = query_contacts(args.query)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.format == "csv":
        print(to_csv(rows))
    elif args.format == "tsv":
        if rows:
            for n, p, e in rows:
                print(f"{n}\t{p}\t{e}")
    else:
        print(to_markdown(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
