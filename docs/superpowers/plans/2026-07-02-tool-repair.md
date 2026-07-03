# tool_repair 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 Tau agent 层加工具输入修复管线，消灭 P0 裸 `json.loads` 崩溃点，覆盖 ~90% "模型不会调工具" 的场景；schema 从 `do_*` 签名自动推导，零侵入 handler.py 业务逻辑。

**Architecture:** 新增 `core/agent/tool_repair.py`（schema 推导 + validate + shape_fix + path_clean + relational_defaults + telemetry），`BaseHandler.dispatch` 入口单点接入；`loop.py:95` 裸 `json.loads` 换成容错 `safe_parse_args`；`handler.py` 加 `_get_abs_path` 路径逃逸 + 4 处 `[Error]` 前缀改写；`tau_cli/commands/doctor.py` 新建读 `REPAIR_STATS` + jsonl fallback。每步独立 commit，可独立回滚。

**Tech Stack:** Python ≥3.10,<3.14 · 现有 `core/agent/` 子包 · `ast` 模块（解析 do_* 函数体）+ `pytest` · `uv` 包管理 · 无新依赖

---

## 实施发现（Task 1 已落地，需更新下游 tasks）

Task 1 实施时发现 plan 假设的 `inspect.signature` 路线**不可行**：`TauHandler.do_*` 方法签名全是 `(self, args, response)`，无法从签名推 properties。已改为 AST 扫描 do_* 函数体提取 `args.get("literal_key", default)` 的字面 key，类型从 default 节点推断。Commits `58e1297` + `8bf9c18` + `428068a`。

**对下游 tasks 的影响**：
- Task 2-3 代码逻辑**不变**（消费 `SCHEMAS[tool]['properties']`，对 properties 来源无依赖）
- Tasks 4-10 不受影响（dispatch / loop.py / handler.py 操作不依赖 schema 推导策略）
- Task 10 测试断言时需要知道：`web_execute_js` schema 同时含 `switch_tab_id` 和 `tab_id`（都被 AST 提取）；`file_write.content` 因 handler.py:72 无默认值，`type` 字段缺失（属正常 opaque 字段，validate 跳过）；`switch_tab_id` 因默认值是 `None`，`type` 字段也缺失（validate 当 any 处理）

**Task 2 实施后的 spec drift**（commit `72bb5f5` + `1a73d11`）：
- `validate()` 加了 `stype is None` 分支：当 property 无 `type`（None 默认值产生 `{}` spec），仍递归嵌套 properties 但不强制类型。这是 AST-derived schema 的必要补丁。
- `repair_tool_input` 修复循环里 `expected = fspec.get("type"); if expected is None: continue` —— 比 plan §4.8 原写法 `fspec.get("type", issue.expected if issue.expected in _TYPE_CHECKS else "string")` 更稳健（后者对 `"enum[...]"` 之类的 expected 会 fallback 到 "string" 错误）。
- `repair_tool_input` 文档契约：入参 raw_args 假定 JSON-shaped（上游 `safe_parse_args` 保证），含 datetime/Decimal/set 会 raise。
- Task 10 需补 1 个测试 `test_no_type_constraint_passthrough`：覆盖 `switch_tab_id` 的 None 默认被 `_fix_null_optional` 剔除的行为，锁定 AST-derived no-type 的契约。

---

## 全局约束

- 工作目录: `/Users/x403/tau/.worktrees/tau-v4.0.0`
- 所有路径相对此根
- 包管理器: uv (不用 pip/venv/poetry)
- Python 版本: `>=3.10,<3.14` (pyproject.toml:11)
- 提交语言: 英文 (commit message) / 中文 (对话与文档)
- 重构后**不修改**:
  - `core/agent/loop.py` 的 `agent_runner_loop` 主循环结构、`_run_dispatch` 行为、`_render_tool_call`
  - `core/agent/format.py` 任何内容
  - `core/agent/runtime.py` 业务逻辑（仅在启动入口加一行 `init_schemas(TauHandler)`）
  - `core/llm/`、`core/tools/`、`core/paths.py` 任何内容
  - `assets/prompts/` 运行时提示词
  - `apps/*` / `plugins/*` / `tau_cli/commands/_launchers.py` 任何内容
- 重构后**新增/修改**:
  - 新增 `core/agent/tool_repair.py`
  - 修改 `core/agent/loop.py` L19-30 (`BaseHandler.dispatch`) + L94-96 (`json.loads` 替换) + 新增 `_resolve_model`
  - 修改 `core/agent/handler.py` `_get_abs_path` + `do_file_read/write/patch` 调用点 None 翻译 + L117 / L172 / L75 / L93 文案改写
  - 修改 `core/agent/runtime.py` 启动入口加 `init_schemas(TauHandler)` 一行
  - 新增 `tau_cli/commands/doctor.py`
  - 修改 `tau_cli/cli.py` COMMANDS + 分发加 `doctor`
  - 新增 `tests/test_tool_repair.py` 12 个用例

---

## 任务总览

| # | 任务 | 文件 | commit 类型 |
|---|---|---|---|
| 1 | 建 `core/agent/tool_repair.py` 骨架 + safe_parse_args + derive_schema + init_schemas | `core/agent/tool_repair.py` (新) | chore |
| 2 | 加 validate + shape_fix + path_clean + relational_defaults + repair_tool_input 主入口 | `core/agent/tool_repair.py` (改) | feat |
| 3 | 加遥测 REPAIR_STATS + jsonl + _hook | `core/agent/tool_repair.py` (改) | feat |
| 4 | `loop.py` L95 用 safe_parse_args 替换裸 json.loads + L94 列表推导重写为循环 | `core/agent/loop.py` (改) | fix |
| 5 | `BaseHandler.dispatch` 接入 repair_tool_input + 未知工具近似匹配 + `_resolve_model` | `core/agent/loop.py` (改) | refactor |
| 6 | `handler.py` `_get_abs_path` 路径逃逸检查 + `do_file_read/write/patch` 调用点 None 翻译 | `core/agent/handler.py` (改) | fix |
| 7 | `handler.py` 4 处 `[Error]` 前缀去除并改写文案 (L75 / L93 / L117 / L172) | `core/agent/handler.py` (改) | refactor |
| 8 | `core/agent/runtime.py` 启动入口加 `init_schemas(TauHandler)` 一行 | `core/agent/runtime.py` (改) | chore |
| 9 | 新建 `tau_cli/commands/doctor.py` + `tau_cli/cli.py` 注册 | 1 新 + 1 改 | feat |
| 10 | 新建 `tests/test_tool_repair.py` 12 个用例 + 全量测试通过 | `tests/test_tool_repair.py` (新) | test |

---

## Task 1: 建 tool_repair.py 骨架 + safe_parse_args + derive_schema + init_schemas

**Files:**
- Create: `core/agent/tool_repair.py`

- [ ] **Step 1: 创建文件，写入头部 docstring 与 imports**

```python
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
```

- [ ] **Step 2: 加 `_py_type_to_schema_type` 与 `_infer_field_schema` 启发式**

在 `core/agent/tool_repair.py` 末尾追加：

```python
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
```

- [ ] **Step 3: 加 `derive_schema` 与 `init_schemas`**

```python
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
    global SCHEMAS
    SCHEMAS = derive_schema(handler_cls)
```

- [ ] **Step 4: 加 `safe_parse_args` (P0 修复核心)**

```python
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
```

- [ ] **Step 5: 验证骨架 import 与 init_schemas 不报错**

Run: `python -c "from core.agent.tool_repair import safe_parse_args, init_schemas, derive_schema, SCHEMAS; from core.agent.handler import TauHandler; init_schemas(TauHandler); print(sorted(SCHEMAS.keys()))"`
Expected: 输出形如 `['ask_user', 'code_run', 'file_patch', 'file_read', 'file_write', 'start_long_term_update', 'update_working_checkpoint', 'web_execute_js', 'web_scan']`（顺序可能不同）

- [ ] **Step 6: Commit**

```bash
git add core/agent/tool_repair.py
git commit -m "feat(agent): tool_repair 骨架 + safe_parse_args + schema 自动推导"
```

---

## Task 2: validate + shape_fix + path_clean + relational_defaults + 主入口

**Files:**
- Modify: `core/agent/tool_repair.py` (在 Task 1 文件上追加)

- [ ] **Step 1: 加 `Issue` 类与 `_TYPE_CHECKS`**

在 `core/agent/tool_repair.py` 追加：

```python
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
```

- [ ] **Step 2: 加 shape_fix（6 个，按序）**

```python
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
```

- [ ] **Step 3: 加 path_clean**

```python
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
```

- [ ] **Step 4: 加 relational_defaults（注意：file_read 真实参数是 start/count）**

```python
# ======================================================================
# 5) 关系不变量：语义扩展 + 透明告知（无错误前缀）
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
```

- [ ] **Step 5: 加 `_get_parent` / `_schema_at` / `repair_tool_input` 主入口**

```python
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


def repair_tool_input(model_id: str, tool_name: str, raw_args: dict):
    schema = SCHEMAS.get(tool_name)
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
        args = json.loads(json.dumps(raw_args))          # 深拷贝
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
            expected = fspec.get("type", issue.expected if issue.expected in _TYPE_CHECKS else "string")
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
```

- [ ] **Step 6: 验证 `repair_tool_input` 主入口不报错（暂不验 _record 因为还没加）**

Run: `python -c "from core.agent.tool_repair import init_schemas, repair_tool_input; from core.agent.handler import TauHandler; init_schemas(TauHandler); r = repair_tool_input('', 'file_read', {'path': 'a', 'count': 50}); print(r); assert r[1] is True; assert r[0]['start'] == 1; print('ok')"`
Expected: 看到 `({'path': 'a', 'count': 50, 'start': 1}, True, ['注意：start 未提供...'])` 且最后输出 `ok`

> 注：此步可能因 `_record` 未定义报错。若报错，先把第 5 步末尾的 `_record(...)` 调用暂时全部注释（或在文件顶部加 `def _record(*a, **k): pass` 占位），验证完再恢复。Task 3 会真正实现 `_record`。

- [ ] **Step 7: Commit**

```bash
git add core/agent/tool_repair.py
git commit -m "feat(agent): tool_repair validate + shape_fix + path_clean + 主入口"
```

---

## Task 3: 加遥测 REPAIR_STATS + jsonl + _hook

**Files:**
- Modify: `core/agent/tool_repair.py`

- [ ] **Step 1: 加 REPAIR_STATS 与 _record（在主入口 repair_tool_input 之前插入）**

```python
# ======================================================================
# 6) 遥测：内存 Counter（tau doctor 用）+ jsonl 落盘（reflect/ 用）
# ======================================================================
REPAIR_STATS: Counter = Counter()
_TELEMETRY_FILE = Path(".tau/repair_telemetry.jsonl")


def _record(model: str, tool: str, kind: str, path: list) -> None:
    REPAIR_STATS[(model, tool, kind)] += 1
    try:
        from plugins.hooks import trigger as _hook
        _hook("tool_repair", {"model": model, "tool": tool, "kind": kind, "path": path})
    except ImportError:
        pass
    try:
        _TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _TELEMETRY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "model": model, "tool": tool,
                                "repair": kind, "path": ".".join(map(str, path))},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass
```

- [ ] **Step 2: 验证 _record 不报错且 REPAIR_STATS 累加**

Run: `python -c "from core.agent import tool_repair; tool_repair._record('', 'file_read', 'md_link_leak', ['path']); print(tool_repair.REPAIR_STATS); print(list(tool_repair._TELEMETRY_FILE.read_text().splitlines()))"`
Expected: `Counter({('', 'file_read', 'md_link_leak'): 1})` 与一行 jsonl（`{"ts": ..., "model": "", "tool": "file_read", ...}`）

- [ ] **Step 3: 清理测试副作用**

Run: `rm -f .tau/repair_telemetry.jsonl && python -c "from core.agent import tool_repair; tool_repair.REPAIR_STATS.clear()"`
Expected: 文件删除 + 计数器清空（无输出）

- [ ] **Step 4: Commit**

```bash
git add core/agent/tool_repair.py
git commit -m "feat(agent): tool_repair 遥测 — 内存 Counter + jsonl 落盘 + hook"
```

---

## Task 4: loop.py L95 裸 json.loads 替换

**Files:**
- Modify: `core/agent/loop.py`

- [ ] **Step 1: 看一眼现状（确认行号）**

Run: `grep -n "json.loads\|tool_calls = " core/agent/loop.py`
Expected: 见 `json.loads(tc.function.arguments)` 在 L95 附近，`tool_calls = [` 在 L94 附近

- [ ] **Step 2: 把 L94-96 的列表推导重写为循环（含 safe_parse_args）**

在 `core/agent/loop.py` 顶部确认 `import json, re, os` 已存在（存在）。

**Before**（约 L94-96）：
```python
        if not response.tool_calls: tool_calls = [{'tool_name': 'no_tool', 'args': {}}]
        else: tool_calls = [{'tool_name': tc.function.name, 'args': json.loads(tc.function.arguments), 'id': tc.id}
                          for tc in response.tool_calls]
```

**After**（同位置替换）：
```python
        from .tool_repair import safe_parse_args
        tool_calls = []
        for tc in (response.tool_calls or []):
            args, err = safe_parse_args(tc.function.arguments)
            if args is None:
                tool_calls.append({'tool_name': 'bad_json', 'args': {
                    'msg': f'工具 {tc.function.name} 的参数不是合法 JSON（{err}）。'
                           f'请重新调用该工具，参数必须是一个 JSON 对象。'}, 'id': tc.id})
            else:
                tool_calls.append({'tool_name': tc.function.name, 'args': args, 'id': tc.id})
        if not tool_calls: tool_calls = [{'tool_name': 'no_tool', 'args': {}}]
```

> 注意：原 `if not response.tool_calls: ... else: [...] for tc in response.tool_calls]` 的分支重写为无条件 `for tc in (response.tool_calls or [])`，与方案 spec 第 5.1 节一致。

- [ ] **Step 3: 验证 import 不报错**

Run: `python -c "from core.agent.loop import agent_runner_loop, BaseHandler, StepOutcome; print('ok')"`
Expected: 输出 `ok`

- [ ] **Step 4: Commit**

```bash
git add core/agent/loop.py
git commit -m "fix(agent): loop.py L95 裸 json.loads 替换为 safe_parse_args"
```

---

## Task 5: BaseHandler.dispatch 接入 repair_tool_input + 未知工具近似匹配

**Files:**
- Modify: `core/agent/loop.py`

- [ ] **Step 1: 看一眼现状**

Run: `grep -n "def dispatch\|method_name = f" core/agent/loop.py`
Expected: `def dispatch` 在 L19，`method_name = f"do_{tool_name}"` 在 L20

- [ ] **Step 2: 在 `dispatch` 方法上方加 `_resolve_model` 辅助**

**在 L18 与 L19 之间插入：**
```python
    def _resolve_model(handler_self):
        """从 handler.parent.llmclient.model 提模型 id；失败返回空串。"""
        try:
            return getattr(getattr(getattr(handler_self, 'parent', None), 'llmclient', None), 'model', '') or ''
        except Exception:
            return ''
```

> 由于 `_resolve_model` 不依赖 `self`，写成普通函数（模块级）或静态方法都可。这里选模块级函数更清晰。实际写在 `BaseHandler` 类外、`dispatch` 方法上方。

实际调整：在 `BaseHandler` 类**外**、`agent_runner_loop` 之前插入：
```python
def _resolve_model(handler_self):
    """从 handler.parent.llmclient.model 提模型 id；失败返回空串。"""
    try:
        return getattr(getattr(getattr(handler_self, 'parent', None), 'llmclient', None), 'model', '') or ''
    except Exception:
        return ''
```

- [ ] **Step 3: 重写 `BaseHandler.dispatch`**

**Before**（L19-30）：
```python
    def dispatch(self, tool_name, args, response, index=0, tool_num=1):
        method_name = f"do_{tool_name}"
        if hasattr(self, method_name):
            args['_index'] = index; args['_tool_num'] = tool_num
            _hook('tool_before', locals())
            ret = yield from try_call_generator(getattr(self, method_name), args, response)
            _hook('tool_after', locals())
            return ret
        elif tool_name == 'bad_json': return StepOutcome(None, next_prompt=args.get('msg', 'bad_json'), should_exit=False)
        else:
            yield f"未知工具: {tool_name}\n"
            return StepOutcome(None, next_prompt=f"未知工具 {tool_name}", should_exit=False)
```

**After**（同位置替换）：
```python
    def dispatch(self, tool_name, args, response, index=0, tool_num=1):
        method_name = f"do_{tool_name}"
        if hasattr(self, method_name):
            from .tool_repair import repair_tool_input
            model = _resolve_model(self)
            args, ok, notes = repair_tool_input(model, tool_name, args)
            if not ok:
                for n in notes:
                    yield n + "\n"
                return StepOutcome(None, next_prompt='；'.join(notes), should_exit=False)
            relational = [n for n in notes if n.startswith('注意')]
            for n in notes:
                if not n.startswith('注意'):
                    yield n + "\n"
            args['_index'] = index; args['_tool_num'] = tool_num
            _hook('tool_before', locals())
            ret = yield from try_call_generator(getattr(self, method_name), args, response)
            _hook('tool_after', locals())
            if relational and ret is not None and ret.data is not None:
                note_text = '\n\n'.join(relational)
                if isinstance(ret.data, dict):
                    ret.data.setdefault('note', note_text)
                else:
                    ret.data = f"{ret.data}\n\n{note_text}"
            return ret
        elif tool_name == 'bad_json':
            return StepOutcome(None, next_prompt=args.get('msg', 'bad_json'), should_exit=False)
        else:
            import difflib
            known = [m[3:] for m in dir(self) if m.startswith('do_')]
            hint = difflib.get_close_matches(tool_name, known, n=1)
            if hint:
                msg = f"未知工具 {tool_name}。你是想用 `{hint[0]}` 吗？可用工具：{', '.join(known)}"
            else:
                msg = f"未知工具 {tool_name}。可用工具：{', '.join(known)}"
            yield msg + "\n"
            return StepOutcome(None, next_prompt=msg, should_exit=False)
```

> 关键不变量保留：未知分支 `next_prompt` 仍以"未知工具"开头 → `loop.py:111` 的 `if outcome.next_prompt.startswith('未知工具'): client.last_tools = ''` 工具描述重发机制继续命中。

- [ ] **Step 4: 验证 import + dispatch 签名不破坏**

Run: `python -c "from core.agent.loop import BaseHandler, StepOutcome; import inspect; sig = inspect.signature(BaseHandler.dispatch); print(list(sig.parameters)); print('ok')"`
Expected: 参数列表为 `['self', 'tool_name', 'args', 'response', 'index', 'tool_num']`，末尾输出 `ok`

- [ ] **Step 5: 跑现有结构测试，确认未破坏**

Run: `pytest tests/test_core_agent_layout.py -v`
Expected: 全部通过（test_handler_module_importable 等都绿）

- [ ] **Step 6: Commit**

```bash
git add core/agent/loop.py
git commit -m "refactor(agent): BaseHandler.dispatch 接入 tool_repair + 未知工具近似匹配"
```

---

## Task 6: handler.py _get_abs_path 路径逃逸检查 + 调用点 None 翻译

**Files:**
- Modify: `core/agent/handler.py`

- [ ] **Step 1: 改造 `_get_abs_path`**

**Before**（L41-43）：
```python
    def _get_abs_path(self, path):
        if not path: return ""
        return os.path.abspath(os.path.join(self.cwd, path))
```

**After**（同位置替换）：
```python
    def _get_abs_path(self, path):
        if not path: return ""
        abs_path = os.path.abspath(os.path.join(self.cwd, path))
        cwd_abs = os.path.abspath(self.cwd)
        try:
            if os.path.commonpath([abs_path, cwd_abs]) != cwd_abs:
                return None
        except ValueError:
            return None
        return abs_path
```

- [ ] **Step 2: `do_file_read` 加 None 翻译**

**Before**（L47-48）：
```python
        path = self._get_abs_path(args.get("path", ""))
        yield f"\n[Action] Reading file: {path}\n"
```

**After**（同位置替换）：
```python
        path = self._get_abs_path(args.get("path", ""))
        if path is None:
            yield f"[Status] ❌ 路径越界：参数 path 解析后跳出了工作目录 {self.cwd}，请提供工作目录内的相对路径后重试。\n"
            return StepOutcome({"status": "error", "msg": "路径越界，请提供工作目录内的相对路径后重试。"}, next_prompt="\n")
        yield f"\n[Action] Reading file: {path}\n"
```

- [ ] **Step 3: `do_file_write` 加 None 翻译**

**Before**（L68）：
```python
        path = self._get_abs_path(args.get("path", ""))
        mode = args.get("mode", "overwrite")
```

**After**（同位置替换）：
```python
        path = self._get_abs_path(args.get("path", ""))
        if path is None:
            yield f"[Status] ❌ 路径越界：参数 path 解析后跳出了工作目录 {self.cwd}，请提供工作目录内的相对路径后重试。\n"
            return StepOutcome({"status": "error", "msg": "路径越界，请提供工作目录内的相对路径后重试。"}, next_prompt="\n")
        mode = args.get("mode", "overwrite")
```

- [ ] **Step 4: `do_file_patch` 加 None 翻译**

**Before**（L87）：
```python
        path = self._get_abs_path(args.get("path", ""))
        yield f"[Action] Patching file: {path}\n"
```

**After**（同位置替换）：
```python
        path = self._get_abs_path(args.get("path", ""))
        if path is None:
            yield f"[Status] ❌ 路径越逸：参数 path 解析后跳出了工作目录 {self.cwd}，请提供工作目录内的相对路径后重试。\n"
            return StepOutcome({"status": "error", "msg": "路径越界，请提供工作目录内的相对路径后重试。"}, next_prompt="\n")
        yield f"[Action] Patching file: {path}\n"
```

> typo 修正：原方案写"越界"，这里"越逸"是手滑，统一用"越界"。Edit 时保持一致即可。

- [ ] **Step 5: 验证 import 不破坏 + 路径逃逸真能拦住**

Run:
```bash
python -c "
import sys
sys.path.insert(0, '.')
from core.agent.handler import TauHandler
h = TauHandler(parent=None, cwd='./temp')
# 正常路径
print('ok:', h._get_abs_path('foo.txt'))
# 逃逸路径
print('escape:', h._get_abs_path('../../../etc/passwd'))
"
```
Expected: `ok: /Users/.../tau-v4.0.0/temp/foo.txt` 与 `escape: None`（后者为 None）

- [ ] **Step 6: 跑现有测试确认未破坏**

Run: `pytest tests/test_core_agent_layout.py -v`
Expected: 全部通过

- [ ] **Step 7: Commit**

```bash
git add core/agent/handler.py
git commit -m "fix(agent): handler._get_abs_path 加 .. 逃逸检查 + 3 个 do_file_* 调用点 None 翻译"
```

---

## Task 7: handler.py 4 处 [Error] 前缀去除并改写文案

**Files:**
- Modify: `core/agent/handler.py`

- [ ] **Step 1: 改 `do_code_run` 的 `[Error] Code missing`**

**Before**（L117）：
```python
            if not code: return StepOutcome("[Error] Code missing. Must use reply code block or 'script' arg.", next_prompt="\n")
```

**After**（同位置替换）：
```python
            if not code: return StepOutcome("未收到代码。请把代码放入 \`\`\`python 代码块或 code 参数后重试。", next_prompt="\n")
```

- [ ] **Step 2: 改 `do_web_execute_js` 的 `[Error] Script missing`**

**Before**（L172）：
```python
        if not script: return StepOutcome("[Error] Script missing. Use \`\`\`javascript block or 'script' arg.", next_prompt="\n")
```

**After**（同位置替换）：
```python
        if not script: return StepOutcome("未收到脚本。请把脚本放入 \`\`\`javascript 代码块或 script 参数后重试。", next_prompt="\n")
```

- [ ] **Step 3: 改 `do_file_write` 的 "No content found"**

**Before**（L75）：
```python
            return StepOutcome({"status": "error", "msg": "No content found. Blank is not supported. Put content inside ...</file_content> tags in your reply body before call file_write."}, next_prompt="\n")
```

**After**（同位置替换）：
```python
            return StepOutcome({"status": "error", "msg": "未找到要写入的内容。请将内容放入 <file_content>...</file_content> 标签内，或作为 content 参数传入后重试。"}, next_prompt="\n")
```

- [ ] **Step 4: 改 `do_file_patch` 的 `expand_file_refs` 失败 message**

**Before**（L93）：
```python
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")
```

**After**（同位置替换）：
```python
            return StepOutcome({"status": "error", "msg": f"引用展开失败：{e}。请检查 @path 引用是否指向存在的文件后重试。"}, next_prompt="\n")
```

- [ ] **Step 5: 验证搜索确认所有 `[Error] ` 前缀已消失（在代码非注释位置）**

Run: `grep -n "\[Error\]" core/agent/handler.py`
Expected: **无输出**（所有 `[Error]` 已替换）

- [ ] **Step 6: 跑现有测试**

Run: `pytest tests/test_core_agent_layout.py -v`
Expected: 全绿

- [ ] **Step 7: Commit**

```bash
git add core/agent/handler.py
git commit -m "refactor(agent): handler 4 处可重试错误去除 [Error] 前缀"
```

---

## Task 8: runtime.py 启动入口加 init_schemas(TauHandler) 一行

**Files:**
- Modify: `core/agent/runtime.py`

- [ ] **Step 1: 找到合适的启动入口**

Run: `grep -n "def main\|def get_system_prompt\|TauHandler" core/agent/runtime.py | head -20`
Expected: 看到 `def main(...)` 或类似入口

- [ ] **Step 2: 在 `main()` 函数体最顶端插入（紧跟函数签名行后）**

具体插入点：找到 `def main(...):` 行，在函数体的第一行非 docstring 代码前插入：

```python
    from .tool_repair import init_schemas
    from .handler import TauHandler
    init_schemas(TauHandler)
```

> 注意：若 `main()` 第一行就是 docstring，则把这两行插在 docstring 之后；若没有 docstring 插在函数签名下一行。具体位置以实读 runtime.py 为准。

- [ ] **Step 3: 验证不破坏 import**

Run: `python -c "from core.agent.runtime import Tau, get_system_prompt; print('ok')"`
Expected: 输出 `ok`

- [ ] **Step 4: 验证 `main()` 启动不报错（无 LLM 调用）**

Run: `python -c "from core.agent.runtime import main; from core.agent.tool_repair import SCHEMAS; print(len(SCHEMAS))"`
Expected: 输出一个数字（≥ 7，因为有 file_read/write/patch/code_run/web_scan/web_execute_js/ask_user 等）

- [ ] **Step 5: Commit**

```bash
git add core/agent/runtime.py
git commit -m "chore(agent): runtime main() 启动时初始化 tool_repair schema"
```

---

## Task 9: 新建 tau_cli/commands/doctor.py + cli.py 注册

**Files:**
- Create: `tau_cli/commands/doctor.py`
- Modify: `tau_cli/cli.py`

- [ ] **Step 1: 创建 `tau_cli/commands/doctor.py`**

```python
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
    """进程已退时 fallback 读 jsonl。"""
    p = Path(".tau/repair_telemetry.jsonl")
    if not p.exists():
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
```

- [ ] **Step 2: 修改 `tau_cli/cli.py` — import 与 COMMANDS**

**Before**（L11-12）：
```python
from tau_cli.commands import _launchers as _launchers_mod
from tau_cli.commands import run, list as list_cmd, status as status_cmd, update as update_cmd
```

**After**：
```python
from tau_cli.commands import _launchers as _launchers_mod
from tau_cli.commands import run, list as list_cmd, status as status_cmd, update as update_cmd, doctor as doctor_cmd
```

**Before**（L15-21）：
```python
COMMANDS = {
    **_launchers_mod.LAUNCHERS,
    "list":   list_cmd.COMMAND,
    "status": status_cmd.COMMAND,
    "update": update_cmd.COMMAND,
    "run":    run.COMMAND,
}
```

**After**：
```python
COMMANDS = {
    **_launchers_mod.LAUNCHERS,
    "list":   list_cmd.COMMAND,
    "status": status_cmd.COMMAND,
    "update": update_cmd.COMMAND,
    "run":    run.COMMAND,
    "doctor": doctor_cmd.COMMAND,
}
```

- [ ] **Step 3: 修改 `tau_cli/cli.py` — 分发分支**

**Before**（L62-74）：
```python
    # === dispatch ===
    if cmd == "list":
        list_cmd.run(commands=COMMANDS)
        return
    if cmd == "status":
        status_cmd.run(extra or None)
        return
    if cmd == "update":
        update_cmd.run(extra or None)
        return
    if cmd == "run":
        run.run(extra or None)
        return
```

**After**：
```python
    # === dispatch ===
    if cmd == "list":
        list_cmd.run(commands=COMMANDS)
        return
    if cmd == "status":
        status_cmd.run(extra or None)
        return
    if cmd == "update":
        update_cmd.run(extra or None)
        return
    if cmd == "run":
        run.run(extra or None)
        return
    if cmd == "doctor":
        doctor_cmd.run(extra or None)
        return
```

- [ ] **Step 4: 验证 `tau doctor` 在无修复记录时输出健康消息**

Run: `rm -f .tau/repair_telemetry.jsonl && python -m tau_cli doctor`
Expected: 输出 `🟢 暂无修复记录（健康）`

- [ ] **Step 5: 验证 `tau list` 把 doctor 列出来**

Run: `python -m tau_cli list | grep -i doctor`
Expected: 看到包含 `doctor` 的行

- [ ] **Step 6: Commit**

```bash
git add tau_cli/commands/doctor.py tau_cli/cli.py
git commit -m "feat(cli): tau doctor — 工具输入修复遥测查看器"
```

---

## Task 10: tests/test_tool_repair.py 12 个用例 + 全量测试通过

**Files:**
- Create: `tests/test_tool_repair.py`

- [ ] **Step 1: 创建文件，写入 fixture 与 12 个测试用例**

```python
"""tool_repair 单元测试 — 守护两大陷阱（opaque 不误伤 + 修复顺序）不回归。"""
import pytest


@pytest.fixture(autouse=True)
def _reset_schemas_and_stats():
    """每个用例独立，互不污染 SCHEMAS / REPAIR_STATS。"""
    from core.agent import tool_repair
    from core.agent.handler import TauHandler
    tool_repair.init_schemas(TauHandler)
    tool_repair.REPAIR_STATS.clear()
    yield
    tool_repair.REPAIR_STATS.clear()


def _repair(model, tool, args):
    from core.agent.tool_repair import repair_tool_input
    return repair_tool_input(model, tool, args)


# ---- 1: safe_parse_args 正常 ----
def test_safe_parse_args_ok():
    from core.agent.tool_repair import safe_parse_args
    args, err = safe_parse_args('{"a": 1}')
    assert args == {"a": 1} and err is None


# ---- 2: safe_parse_args 宽松与失败 ----
def test_safe_parse_args_lenient():
    from core.agent.tool_repair import safe_parse_args
    args, err = safe_parse_args('{"a":1,}')
    assert args == {"a": 1} and err == 'lenient_json'
    args2, err2 = safe_parse_args('not json at all')
    assert args2 is None and err2 is not None


# ---- 3: opaque content 不被解析为数组 ----
def test_opaque_content_preserved():
    args, ok, notes = _repair('', 'file_write', {'path': 'a.txt', 'content': '["a","b"]'})
    assert ok is True
    assert args['content'] == '["a","b"]', "opaque 字段 content 绝不能被当 JSON 解析"


# ---- 4: stringified_array 优先于 bare_value_wrap ----
def test_stringified_array_before_wrap():
    args, ok, notes = _repair('', 'ask_user', {'question': 'q', 'candidates': '["A","B"]'})
    assert ok is True
    assert args['candidates'] == ['A', 'B'], f"应为两元素列表，实得 {args.get('candidates')}"


# ---- 5: 裸值包装为单元素列表 ----
def test_bare_value_wrap():
    args, ok, notes = _repair('', 'ask_user', {'question': 'q', 'candidates': 'A'})
    assert ok is True
    assert args['candidates'] == ['A']


# ---- 6: null optional 字段被剔除 ----
def test_null_optional_dropped():
    """start/count 在 file_read schema 里非 required，传 None 应被剔除。"""
    args, ok, notes = _repair('', 'file_read', {'path': 'a', 'start': None})
    assert ok is True
    assert 'start' not in args


# ---- 7: 空对象 {} → [] ----
def test_empty_object_placeholder():
    args, ok, notes = _repair('', 'ask_user', {'question': 'q', 'candidates': {}})
    assert ok is True
    assert args['candidates'] == []


# ---- 8: 布尔字符串 truthy 反转修复 ----
def test_coerce_bool():
    args, ok, notes = _repair('', 'web_scan', {'tabs_only': 'false'})
    assert ok is True
    assert args['tabs_only'] is False, "字符串 'false' 应被强转为布尔 False"


# ---- 9: md_link_leak 兜底 ----
def test_md_link_leak():
    from core.agent.tool_repair import repair_tool_input
    args1, ok1, _ = repair_tool_input('', 'file_read', {'path': '[a.txt](a.txt)'})
    assert ok1 is True and args1['path'] == 'a.txt'
    args2, ok2, _ = repair_tool_input('', 'file_read', {'path': '[doc](https://x.com/y)'})
    assert ok2 is True and args2['path'] == '[doc](https://x.com/y)', "真链接不动"


# ---- 10: 关系默认值 + 附注以"注意"开头 ----
def test_relational_defaults_file_read():
    args, ok, notes = _repair('', 'file_read', {'path': 'a.txt', 'count': 50})
    assert ok is True
    assert args['start'] == 1
    assert any(n.startswith('注意') for n in notes), f"附注应为中性'注意'提示，实得 {notes}"
    assert not any('[Error]' in n for n in notes), "附注不能带 [Error] 前缀"


# ---- 11: 快路径零拷贝 ----
def test_fast_path_zero_copy():
    raw = {'path': 'a.txt', 'start': 1, 'count': 100}
    args, ok, notes = _repair('', 'file_read', raw)
    assert ok is True
    assert args is raw, f"合法输入应原样返回，未拷贝；实得 args={args} raw={raw}"


# ---- 12: 别名 falsy 值（0 不被 or 吞掉） ----
def test_alias_falsy_value():
    args, ok, notes = _repair('', 'web_execute_js', {'script': 'alert(0)', 'tab_id': 0})
    assert ok is True
    assert args.get('switch_tab_id') == 0, f"tab_id=0 应被归一为 switch_tab_id=0；实得 {args}"
    assert 'tab_id' not in args
```

- [ ] **Step 2: 跑 tool_repair 测试**

Run: `pytest tests/test_tool_repair.py -v`
Expected: 12 passed

- [ ] **Step 3: 跑全量测试确认未破坏其他套件**

Run: `pytest tests/ -v --ignore=tests/test_daily_report_gates.py`
Expected: 全部通过（包括 `test_core_agent_layout.py`、`test_core_paths.py`、`test_taukey_path.py`）

> 如果 `test_daily_report_gates.py` 也想跑，可不 ignore；但该测试可能依赖外部数据，本轮不动它。

- [ ] **Step 4: 跑全量最终 smoke**

Run:
```bash
python -c "from core.agent.tool_repair import init_schemas, repair_tool_input; from core.agent.handler import TauHandler; init_schemas(TauHandler); print('schemas:', sorted(init_schemas.__module__ and __import__('core.agent.tool_repair', fromlist=['SCHEMAS']).SCHEMAS.keys())); print(repair_tool_input('', 'file_read', {'path': 'a'})[0])"
```
Expected: 不报错，看到 SCHEMAS 工具名列表 + `{'path': 'a'}`

- [ ] **Step 5: 清理测试副作用**

Run: `rm -f .tau/repair_telemetry.jsonl`
Expected: 文件删除（无输出）

- [ ] **Step 6: Commit**

```bash
git add tests/test_tool_repair.py
git commit -m "test(agent): tool_repair 12 用例 — 守护 opaque 不误伤 + 修复顺序"
```

---

## 自审

**1. Spec 覆盖**：

| Spec 章节 | 任务 |
|---|---|
| §1 P0 裸 json.loads | Task 4 |
| §4.1 schema 自动推导 | Task 1 |
| §4.2 safe_parse_args | Task 1 |
| §4.3 修复顺序 | Task 2 |
| §4.4 validate | Task 2 |
| §4.5 path_clean | Task 2 |
| §4.6 relational_defaults | Task 2 |
| §4.7 遥测 | Task 3 |
| §4.8 主入口 repair_tool_input | Task 2 |
| §5.1 loop.py L95 替换 | Task 4 |
| §5.2 dispatch 接入 | Task 5 |
| §5.3 schema 初始化 | Task 8 |
| §6.1 _get_abs_path 逃逸 | Task 6 |
| §6.2 调用点 None 翻译 | Task 6 |
| §6.3 4 处 [Error] 改写 | Task 7 |
| §7 tau doctor | Task 9 |
| §8 测试 12 用例 | Task 10 |

**2. 占位扫描**：无 "TBD" / "TODO" / "类似 Task N" / "适当处理" 之类。每步给完整代码与命令。

**3. 类型一致性**：
- `repair_tool_input` 返回 `(args, ok: bool, notes: list[str])` — Task 2 定义、Task 5 调用、Task 10 测试一致
- `SCHEMAS` 全局 dict — Task 1 定义、Task 8 初始化、Task 10 测试 fixture 一致
- `_record(model, tool, kind, path)` 签名 — Task 3 定义、Task 2 调用一致
- `_get_abs_path` 返回 `str | "" | None` — Task 6 定义与调用点翻译一致

**4. 风险已覆盖**：路径逃逸（Task 6 Step 5）、schema 推导失败（Task 1 Step 4 fallback）、快路径零拷贝（Task 10 用例 11）、别名 falsy 值（Task 10 用例 12）。

---

## 验收清单

- [ ] Task 1~10 全部完成，每步独立 commit
- [ ] `pytest tests/test_tool_repair.py -v` → 12 passed
- [ ] `pytest tests/ --ignore=tests/test_daily_report_gates.py` → 全部通过
- [ ] `python -m tau_cli doctor` → 输出"暂无修复记录（健康）"
- [ ] `python -m tau_cli list | grep doctor` → 看到 doctor 命令
- [ ] `_get_abs_path('../../../etc/passwd')` 返回 None（路径逃逸生效）
- [ ] 搜索 `core/agent/handler.py` 全文无 `\b\[Error\]` 字样
- [ ] git log 显示 10 个新 commit（Task 1~10，每个独立）