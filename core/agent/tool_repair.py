"""
tool_repair.py — 工具输入修复层（validate-first harness repair）

设计原则：
  1. 先校验、再修复：合法输入永不触碰，只沿校验器指出的 issue 路径
     花修复预算（预处理会误伤，如 file_write.content 恰好是 JSON 文本）。
  2. 修复顺序敏感：字符串化数组解析必须在裸值包装之前，
     否则 '["a","b"]' 会被包成 ['["a","b"]'] 而非 ['a','b']。
  3. opaque 字段（code/script/content）永不修复、永不清洗。
  4. 修不了的返回可读提示（无 [Error] 前缀），经 StepOutcome.next_prompt
     回传模型自然重试 —— 绝不 raise（dispatch 是生成器，raise 会炸 loop）。
  5. 每次修复记录遥测：model × tool × repair_kind，落盘 jsonl 喂 reflect/。
"""
from __future__ import annotations
import json, re, time, inspect
from pathlib import Path
from typing import Any, Callable
from collections import Counter

# 进程级 SCHEMAS（由 init_schemas(handler_cls) 填充一次）
SCHEMAS: dict[str, dict] = {}

# 启发式 opaque 字段名集合
_OPAQUE_HINT_NAMES = frozenset({
    "code", "script", "content", "old_content", "new_content",
    "key_info", "prompt", "question",
})

# 启发式 path 字段名集合
_PATH_HINT_NAMES = frozenset({
    "path", "save_to_file",
})

# 已知别名映射（field_name -> [alias, ...]）
_ALIAS_HINTS: dict[str, list[str]] = {
    "switch_tab_id": ["tab_id"],
}


def _py_type_to_schema_type(t: type) -> str:
    if t is bool: return "boolean"
    if t is int: return "integer"
    if t is float: return "number"
    if t is str: return "string"
    if t is list: return "array"
    if t is dict: return "object"
    return "string"


def _infer_field_schema(name: str, param: inspect.Parameter) -> dict:
    """从 inspect.Parameter 推导 schema spec。opaque/path/aliases 用启发式。"""
    spec: dict = {}
    ann = param.annotation
    if ann is inspect.Parameter.empty:
        ann = None
    if ann is bool:
        spec["type"] = "boolean"
    elif ann is int:
        spec["type"] = "integer"
    elif ann is float:
        spec["type"] = "number"
    elif ann is str:
        spec["type"] = "string"
    elif ann is list:
        spec["type"] = "array"
    elif ann is dict:
        spec["type"] = "object"
    elif param.default is not inspect.Parameter.empty:
        spec["type"] = _py_type_to_schema_type(type(param.default))
    else:
        spec["type"] = "string"
    # 启发式
    if name in _OPAQUE_HINT_NAMES:
        spec["opaque"] = True
    if name in _PATH_HINT_NAMES:
        spec["type"] = "path"
    if name in _ALIAS_HINTS:
        spec["aliases"] = list(_ALIAS_HINTS[name])
    return spec


def derive_schema(handler_cls) -> dict[str, dict]:
    """扫描 handler_cls 的 do_* 方法签名（跳过 do_no_tool），生成 TOOL_SCHEMAS。"""
    schemas: dict[str, dict] = {}
    for attr_name in dir(handler_cls):
        if not attr_name.startswith("do_") or attr_name == "do_no_tool":
            continue
        tool_name = attr_name[3:]
        try:
            sig = inspect.signature(getattr(handler_cls, attr_name))
        except (ValueError, TypeError):
            continue
        props: dict[str, dict] = {}
        for pname, param in sig.parameters.items():
            if pname in ("args", "response", "self"):
                continue
            props[pname] = _infer_field_schema(pname, param)
        schemas[tool_name] = {"type": "object", "properties": props}
    return schemas


def init_schemas(handler_cls) -> None:
    """由 runtime 启动入口调用一次，填充进程级 SCHEMAS。"""
    SCHEMAS.clear()
    SCHEMAS.update(derive_schema(handler_cls))


# ======================================================================
# 0) 畸形 JSON 容错解析（供 loop.py 使用，修 P0 崩溃点）
# ======================================================================
def safe_parse_args(raw: str):
    """返回 (args_dict|None, err_note|None)。失败时调用方合成 bad_json 调用。"""
    try:
        return json.loads(raw), None
    except Exception:
        s = re.sub(r'^```(?:json)?\s*|\s*```$', '', (raw or '').strip())
        s = re.sub(r',\s*([}\]])', r'\1', s)
        try:
            return json.loads(s), 'lenient_json'
        except Exception as e:
            return None, str(e)