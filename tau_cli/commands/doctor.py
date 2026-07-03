"""tau doctor — 工具输入修复遥测查看器"""
import sys, json
from pathlib import Path

COMMAND = {
    "name": "doctor",
    "help": "查看工具输入修复遥测",
    "desc": "读取 REPAIR_STATS 内存计数 / .tau/repair_telemetry.jsonl 落盘，打印 model × tool × repair_kind 矩阵",
    "cmd": None,
    "internal": True,
}


def _read_fallback_jsonl(limit: int = 200) -> list[dict]:
    """进程已退时 fallback 读 jsonl。优先 tool_repair 锚定的路径，找不到再退回 CWD 相对路径。"""
    p = None
    try:
        from core.agent.tool_repair import _get_telemetry_file
        p = _get_telemetry_file()
    except Exception:
        p = Path(".tau/repair_telemetry.jsonl")
    if not p or not p.exists():
        return []
    out = []
    try:
        with p.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        for line in lines:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except OSError:
        pass
    return out


def run(args=None):
    from core.agent import tool_repair
    stats = dict(tool_repair.REPAIR_STATS)
    if not stats:
        records = _read_fallback_jsonl()
        for r in records:
            key = (r.get("model", ""), r.get("tool", ""), r.get("repair", ""))
            stats[key] = stats.get(key, 0) + 1
    if not stats:
        print("🟢 暂无修复记录（健康）")
        return
    from collections import Counter
    by_model: dict[str, Counter] = {}
    for (model, tool, kind), n in stats.items():
        by_model.setdefault(model or "<unknown>", Counter())[(tool, kind)] += n
    print(f"🔧 工具输入修复遥测 — 总修复次数: {sum(stats.values())}")
    for model, ctr in sorted(by_model.items()):
        print(f"\n## Model: {model}")
        print(f"  {'tool':<25} {'repair_kind':<22} {'count':>5}")
        for (tool, kind), n in sorted(ctr.items(), key=lambda x: -x[1]):
            print(f"  {tool:<25} {kind:<22} {n:>5}")
    records = _read_fallback_jsonl(20)
    if records:
        print(f"\n最近 {len(records)} 条落盘记录（.tau/repair_telemetry.jsonl）：")
        for r in records[-10:]:
            print(f"  ts={r.get('ts', 0):.0f}  {r.get('tool','?'):<20} {r.get('repair','?'):<22} path={r.get('path','?')}")