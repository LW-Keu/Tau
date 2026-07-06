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

    def _type_from_node(node) -> dict:
        """返回 {'type': '...'} spec，或空 dict 表示无 type 约束。"""
        if isinstance(node, ast.Constant):
            v = node.value
            if v is None: return {}               # None 默认 → 无 type 约束（validate 当 any）
            if isinstance(v, bool): return {"type": "boolean"}
            if isinstance(v, int): return {"type": "integer"}
            if isinstance(v, float): return {"type": "number"}
            if isinstance(v, str): return {"type": "string"}
            if isinstance(v, list): return {"type": "array"}
            if isinstance(v, dict): return {"type": "object"}
        if isinstance(node, ast.List):  return {"type": "array"}
        if isinstance(node, ast.Dict):  return {"type": "object"}
        return {}                                  # 兜底：无 type 约束

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
        props[key] = _type_from_node(default_node)

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
        # 过滤框架注入 key（BaseHandler.dispatch 设 _index/_tool_num，非模型面）
        props = {k: v for k, v in props.items() if not k.startswith("_")}
        # 收集所有 alias 目标，稍后剔除（避免一个字段既作为主 key 又作为别名的污染）
        alias_targets = set()
        for pname, spec in props.items():
            for a in _ALIAS_HINTS.get(pname, []):
                alias_targets.add(a)
        props = {k: v for k, v in props.items() if k not in alias_targets}
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
    """填充进程级 SCHEMAS，并注入 handler_cls.TOOL_SCHEMAS（dispatch 注入路径用）。

    若 handler_cls 已自举 TOOL_SCHEMAS（handler.py 模块体 import 时推导），直接复用，
    避免二次 AST 扫描。
    """
    existing = getattr(handler_cls, 'TOOL_SCHEMAS', None)
    derived = dict(existing) if existing else derive_schema(handler_cls)
    SCHEMAS.clear()
    SCHEMAS.update(derived)
    handler_cls.TOOL_SCHEMAS = dict(derived)


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


# ======================================================================
# 6) 遥测：内存 Counter（tau doctor 用）+ jsonl 落盘（reflect/ 用）
# ======================================================================
REPAIR_STATS: Counter = Counter()


def _get_telemetry_file() -> Path:
    """锚到 core.paths.TEMP/.tau/，避免 `tau doctor` 在不同 CWD 下找不到 jsonl。

    core.paths 懒加载，避免模块加载时循环依赖（tool_repair 是 schema 入口）。
    """
    from core.paths import TEMP
    return TEMP / ".tau" / "repair_telemetry.jsonl"


def _record(model: str, tool: str, kind: str, path: list) -> None:
    """每次修复 +1；hook 失败/落盘失败静默吞掉，不影响主流程。"""
    REPAIR_STATS[(model, tool, kind)] += 1
    try:
        from plugins.hooks import trigger as _hook
        _hook("tool_repair", {"model": model, "tool": tool, "kind": kind, "path": path})
    except ImportError:
        pass
    try:
        f = _get_telemetry_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "model": model, "tool": tool,
                                "repair": kind, "path": ".".join(map(str, path))},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


# ======================================================================
# 2) 递归校验器：返回带精确路径的 Issue 列表（不短路）
# ======================================================================
class Issue:
    __slots__ = ("path", "expected", "actual", "value")
    def __init__(self, path, expected, actual, value):
        self.path, self.expected, self.actual, self.value = path, expected, actual, value
    def human(self):
        return f"参数 `{'.'.join(map(str, self.path)) or '(root)'}` 期望 {self.expected}，实际收到 {self.actual}"


_TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
    "string":  lambda v: isinstance(v, str),
    "path":    lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number":  lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array":   lambda v: isinstance(v, list),
    "object":  lambda v: isinstance(v, dict),
}


def validate(schema: dict, data: Any, path: list | None = None) -> list[Issue]:
    path = path or []
    issues: list[Issue] = []
    stype = schema.get("type")
    if schema.get("opaque"):
        return issues
    if stype is None:
        # No type constraint (None default in AST extraction produced {} spec)
        # Still recurse into object properties if any
        if isinstance(data, dict) and schema.get("properties"):
            for key, sub in schema["properties"].items():
                if key in data:
                    issues.extend(validate(sub, data[key], path + [key]))
        return issues
    if stype in _TYPE_CHECKS and not _TYPE_CHECKS[stype](data):
        issues.append(Issue(path, stype, type(data).__name__, data))
        return issues
    if stype == "object":
        for key in schema.get("required", []):
            if key not in data:
                issues.append(Issue(path + [key], "required", "missing", None))
        for key, sub in schema.get("properties", {}).items():
            if key in data:
                if data[key] is None and key not in schema.get("required", []):
                    issues.append(Issue(path + [key], sub.get("type", "any"), "null", None))
                else:
                    issues.extend(validate(sub, data[key], path + [key]))
        if "enum" in schema and data not in schema["enum"]:
            issues.append(Issue(path, f"enum{schema['enum']}", repr(data), data))
    elif stype == "array" and "items" in schema:
        for i, item in enumerate(data):
            issues.extend(validate(schema["items"], item, path + [i]))
    elif "enum" in schema and data not in schema["enum"]:
        issues.append(Issue(path, f"enum{schema['enum']}", repr(data), data))
    return issues


# ======================================================================
# 3) 形状修复（顺序即优先级，②必须在③之前，勿调换）
# ======================================================================
_DELETE, _NO_FIX = object(), object()


def _fix_null_optional(v, t):
    return _DELETE if v is None else _NO_FIX


def _fix_stringified_array(v, t):                        # ② 先于 ③
    if t == "array" and isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list): return parsed
            except (json.JSONDecodeError, ValueError): pass
    return _NO_FIX


def _fix_bare_value_wrap(v, t):                          # ③
    if t == "array" and not isinstance(v, (list, dict)) and v is not None:
        return [v]
    return _NO_FIX


def _fix_empty_object_placeholder(v, t):                 # ④
    if t == "array" and isinstance(v, dict) and not v: return []
    return _NO_FIX


def _fix_coerce_bool(v, t):
    if t == "boolean" and isinstance(v, str):
        low = v.strip().lower()
        if low in ("true", "1", "yes"):  return True
        if low in ("false", "0", "no"): return False
    return _NO_FIX


def _fix_coerce_int(v, t):
    if t == "integer" and isinstance(v, (str, float)):
        try: return int(float(v))
        except (ValueError, TypeError): pass
    return _NO_FIX


SHAPE_FIXES = [
    ("null_optional",            _fix_null_optional),
    ("stringified_array",        _fix_stringified_array),
    ("bare_value_wrap",          _fix_bare_value_wrap),
    ("empty_object_placeholder", _fix_empty_object_placeholder),
    ("coerce_bool",              _fix_coerce_bool),
    ("coerce_int",               _fix_coerce_int),
]


# ======================================================================
# 4) PathString 清洗：只处理退化 markdown 自动链接
# ======================================================================
_MD_LINK = re.compile(r"^\[([^\]]+)\]\((?:[a-z]+://)?([^)]+)\)$")


def clean_path_string(v: str) -> str:
    s = v.strip().strip("`")
    m = _MD_LINK.match(s)
    if m and m.group(1).strip() == m.group(2).strip():
        return m.group(1).strip()
    return s


# ======================================================================
# 5) 关系不变量：语义扩展 + 透明告知（无错误前缀）
#    注意：file_read 真实参数是 start/count（不是 offset/limit）
# ======================================================================
DEFAULT_READ_COUNT = 200


def apply_relational_defaults(tool_name: str, args: dict) -> str | None:
    if tool_name == "file_read":
        has_start = "start" in args
        has_count = "count" in args
        if has_count and not has_start:
            args["start"] = 1
            return ("注意：start 未提供，已默认为 1。"
                    "如需从其他行开始，请同时提供 start 与 count 重试。")
        if has_start and not has_count:
            args["count"] = DEFAULT_READ_COUNT
            return (f"注意：count 未提供，已默认为 {DEFAULT_READ_COUNT} 行。"
                    "如需读取更多或更少，请同时提供 start 与 count 重试。")
    return None


# ======================================================================
# 7) 主入口：别名归一 → 校验 → 定点修复 → 复验 → 路径清洗 → 关系默认值
# ======================================================================
def _get_parent(data, path):
    for p in path[:-1]: data = data[p]
    return data, path[-1]


def _schema_at(schema, path):
    for p in path:
        if isinstance(p, int):
            schema = schema.get("items", {})
        else:
            schema = schema.get("properties", {}).get(p, {})
    return schema


def repair_tool_input(model_id: str, tool_name: str, raw_args: dict, schemas: dict | None = None):
    src = schemas if schemas is not None else SCHEMAS
    schema = src.get(tool_name)
    if schema is None or not isinstance(raw_args, dict):
        return raw_args, True, []

    # 别名归一（不用 or：0 也是合法值）
    for field, spec in schema.get("properties", {}).items():
        if field not in raw_args:
            for alias in spec.get("aliases", []):
                if alias in raw_args:
                    raw_args[field] = raw_args.pop(alias)
                    _record(model_id, tool_name, "alias_normalize", [field]); break

    issues = validate(schema, raw_args)
    if not issues:
        args = raw_args                                  # 快路径
    else:
        # 深拷贝：args 假定为 JSON-shaped（上游 safe_parse_args 保证），
        # 若 raw_args 含 datetime/Decimal/set 等非 JSON 值, json.dumps 会 raise。
        # 本契约是"绝不 raise"(dispatch 是生成器, raise 会炸 loop)。
        # 兜底: 序列化失败时退化为 dict() 浅拷贝(失去嵌套共享但不会 raise),
        # 由后续定点修复继续处理可见的字段;不可序列化字段在 do_* 端再处理。
        try:
            args = json.loads(json.dumps(raw_args))      # 深拷贝
        except (TypeError, ValueError):
            args = dict(raw_args)                        # 兜底浅拷贝
        for issue in issues:
            if not issue.path or issue.expected == "required":
                continue
            fspec = _schema_at(schema, issue.path)
            if fspec.get("opaque"):
                continue
            try:
                parent, key = _get_parent(args, issue.path)
            except (KeyError, IndexError, TypeError):
                continue
            current = parent[key] if (isinstance(parent, list) or key in parent) else None
            # Determine expected type — handle the no-type case
            expected = fspec.get("type")
            if expected is None:
                # No type constraint; cannot apply shape_fix; skip
                continue
            for kind, fix in SHAPE_FIXES:
                result = fix(current, expected)
                if result is _NO_FIX:
                    continue
                if result is _DELETE:
                    if isinstance(parent, dict):
                        parent.pop(key, None)
                else:
                    parent[key] = result
                _record(model_id, tool_name, kind, issue.path)
                break
        remaining = validate(schema, args)
        if remaining:
            return args, False, [i.human() + "。请修正后重试。" for i in remaining]

    # 路径字段清洗
    def _walk_paths(sch, node, path):
        if sch.get("type") == "path" and isinstance(node, str):
            cleaned = clean_path_string(node)
            if cleaned != node:
                parent, key = _get_parent(args, path) if path else (None, None)
                if parent is not None: parent[key] = cleaned
                _record(model_id, tool_name, "md_link_leak", path)
        elif sch.get("type") == "object" and isinstance(node, dict):
            for k, sub in sch.get("properties", {}).items():
                if k in node: _walk_paths(sub, node[k], path + [k])
    _walk_paths(schema, args, [])

    note = apply_relational_defaults(tool_name, args)
    notes = []
    if args is not raw_args:
        notes.append("[工具输入已修复]")
    if note:
        notes.append(note)
    return args, True, notes
