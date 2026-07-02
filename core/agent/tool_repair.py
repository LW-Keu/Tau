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
import ast, json, re, time, inspect, textwrap
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


def _extract_arg_keys_from_method(method) -> dict[str, dict]:
    """Walk method AST, collect args.get("literal_key", default) keys + types."""
    try:
        src = textwrap.dedent(inspect.getsource(method))
        tree = ast.parse(src)
    except (OSError, SyntaxError, TypeError, IndentationError):
        return {}

    props: dict[str, dict] = {}

    def _type_from_node(node) -> str:
        if isinstance(node, ast.Constant):
            v = node.value
            if v is None: return "string"
            if isinstance(v, bool): return "boolean"
            if isinstance(v, int): return "integer"
            if isinstance(v, float): return "number"
            if isinstance(v, str): return "string"
            if isinstance(v, list): return "array"
            if isinstance(v, dict): return "object"
        if isinstance(node, ast.List):  return "array"
        if isinstance(node, ast.Dict):  return "object"
        return "string"

    def _is_args_get(call: ast.Call) -> bool:
        f = call.func
        return (
            isinstance(f, ast.Attribute)
            and f.attr == "get"
            and len(call.args) >= 1
        )

    def _is_args_receiver(value) -> bool:
        # 允许 args.get(...) 与 self.args.get(...) 两种写法
        if isinstance(value, ast.Name) and value.id == "args":
            return True
        if isinstance(value, ast.Attribute) and value.attr == "args":
            return True
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_args_get(node):
            continue
        if not _is_args_receiver(node.func.value):
            continue
        # First arg must be a string literal
        first = node.args[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            continue
        key = first.value
        if key in props:
            continue
        # Second positional or `default=` keyword gives the type
        default_node = None
        if len(node.args) >= 2:
            default_node = node.args[1]
        else:
            for kw in node.keywords:
                if kw.arg == "default":
                    default_node = kw.value
                    break
        props[key] = {"type": _type_from_node(default_node)}

    return props


def derive_schema(handler_cls) -> dict[str, dict]:
    """扫描 handler_cls 的 do_* 方法（跳过 do_no_tool），用 AST 提取 args.get 字面 key 生成 properties。"""
    schemas: dict[str, dict] = {}
    for attr_name in dir(handler_cls):
        if not attr_name.startswith("do_") or attr_name == "do_no_tool":
            continue
        tool_name = attr_name[3:]
        method = getattr(handler_cls, attr_name, None)
        if method is None:
            continue
        props = _extract_arg_keys_from_method(method)
        # Overlay opaque/path/aliases 启发式
        for pname, spec in props.items():
            if pname in _OPAQUE_HINT_NAMES:
                spec["opaque"] = True
            if pname in _PATH_HINT_NAMES:
                spec["type"] = "path"
            if pname in _ALIAS_HINTS:
                spec["aliases"] = list(_ALIAS_HINTS[pname])
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