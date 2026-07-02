# tool_repair.py — 工具输入修复层 设计文档

> 日期: 2026-07-02
> 范围: `core/agent/` 子包新增 `tool_repair.py` + `dispatch` 接入 + `loop.py` `json.loads` 替换 + `handler.py` 4 处错误分级 + `_get_abs_path` 路径逃逸检查 + `tau_cli/commands/doctor.py` 遥测命令
> 类型: E-增强型（在已有 agent 层上加修复管线，不引入新子系统）
> 前置: 上一轮 `core/agent` 子包重构已合并（PR-1 ~ PR-5c）

---

## 1. 背景与目标

### 现状问题（基于实读 `core/agent/loop.py` 124 行 + `core/agent/handler.py` 358 行）

| # | 问题 | 证据（真实代码） | 严重度 |
|---|---|---|---|
| 1 | 裸 `json.loads` 崩溃点 | `loop.py:95` `args = json.loads(tc.function.arguments)` 在列表推导式中无异常保护，畸形 JSON 炸掉整个 agent loop | **P0** |
| 2 | 无参数校验/修复层 | `args` 解析后直接进 `dispatch`，无 schema、无修复 | **P0** |
| 3 | 布尔字符串 truthy 反转 | `do_web_scan` `args.get("tabs_only", False)` / `do_web_execute_js` `args.get("no_monitor", False)`：模型传 `"false"` 时行为静默反转 | P1 |
| 4 | 路径字段不设防 | `_get_abs_path` 只 `os.path.join`，无 `..` 逃逸检查、无 markdown 链接清洗 | P1 |
| 5 | 错误前缀滥用 | `handler.py:117` `[Error] Code missing` / `L172` `[Error] Script missing` —— 可重试场景带错误前缀，把模型推入"错误恢复"分布 | P1 |
| 6 | 未知工具提示无引导 | `loop.py:30` `f"未知工具 {tool_name}"` 无近似匹配、无工具清单 | P2 |
| 7 | 别名靠 `or` 硬接 | `handler.py:177` `args.get("switch_tab_id") or args.get("tab_id")`：合法 `0` 被跳过 | P2 |
| 8 | 非确定性 | `loop.py:98` `next_prompts = set()` + `'\n'.join()`，多工具轮次拼接顺序不可复现 | P2 |
| 9 | 修复逻辑散落且无遥测 | `_extract_file_content` / `_extract_code_block` 各自 fallback，无统一统计 | P2 |

**关键架构事实**（决定接入方式，不可违背）：
- `BaseHandler.dispatch()` 是**生成器**，被 `_run_dispatch` 消费 → 修复失败**必须**返回 `StepOutcome(next_prompt=...)`，**绝不能 raise**
- 错误回传通道已存在：`bad_json` 工具分支 → 畸形 JSON 容错复用它
- 真实工具名：`code_run` / `ask_user` / `web_scan` / `web_execute_js` / `file_read` / `file_patch` / `file_write` / `update_working_checkpoint` / `start_long_term_update`（不含前缀 `do_`）
- 真实 `do_file_read` 形参：`path / start / count / keyword / show_linenos`（**不是** `offset / limit`）
- 真实 `do_web_execute_js` 形参：`script / save_to_file / switch_tab_id (或 tab_id 别名) / no_monitor`
- 真实 `do_file_write` 形参：`path / mode / content`（`content` 可缺省，从 response.body 的 `<file_content>` 标签或最后一个代码块提取）
- `_hook('tool_before'/'tool_after', ctx)` 已存在（`plugins/hooks.py` 字符串钩子协议）→ 新增 `_hook('tool_repair', ctx)` 兼容同一签名

### 目标

1. 消灭 P0 崩溃点：`json.loads` 替换为容错 `safe_parse_args`，失败时合成 `bad_json` 工具调用而非抛异常
2. 在 `BaseHandler.dispatch` 入口加修复管线：schema **从 `TauHandler.do_*` 方法签名自动推导**（含启发式识别 opaque/path/aliases），validate-first、shape-fix-second、零拷贝快路径
3. 修不了返回可读重试提示（无 `[Error]` 前缀），经 `next_prompt` 回传模型自然重试 —— **绝不 raise**
4. `_get_abs_path` 加 `..` 逃逸检查，越界返回 `None`，调用方翻译为可重试错误
5. `handler.py` 4 处可重试错误去掉 `[Error]` 前缀；其他 `[Status] ❌` 等环境错误不动
6. 修复事件双出口遥测：内存 `Counter` + `.tau/repair_telemetry.jsonl` 落盘 + `tau doctor` 命令打印 `model × tool × repair_kind` 矩阵
7. `BaseHandler.dispatch` 未知工具分支加近似匹配与可用清单引导

### 非目标

- **不引入** `MODEL_SPECIFIC_FIXES` 模型注册表（先用通用启发式，积累数据后下一轮迭代）
- **不引入** `reflect/` 自动生成 SOP 闭环（仅落盘 jsonl 供后续 reflect 读取，本轮不动 reflect）
- **不动** `core/llm/` / `core/tools/` / `core/paths.py` 业务逻辑
- **不改** `assets/prompts/` 运行时提示词
- **不改** `agent_runner_loop` 主循环结构（除 `json.loads` 替换这一处外）、`_run_dispatch` 行为
- **不改** `_extract_file_content` / `_extract_code_block` fallback 顺序
- **不改** `next_prompts = set()` 的非确定性（属重设计，留后续单独 spec）
- **不引入** typed events / Result 类型 / 钩子协议改造；现有 `_hook(...)` 字符串钩子原样保留

---

## 2. 架构（数据流）

```
                                ┌──────────────────────────────────────────┐
                                │  core/agent/tool_repair.py               │
                                │                                          │
   response.tool_calls ─────────▶  _derive_schema(TauHandler)             │
                                │   └─ 扫描 do_* 形参 → properties         │
                                │       + opaque/path/aliases 启发式         │
                                │                                          │
                                │  repair_tool_input(model, tool, args)    │
                                │   ├─ alias_normalize  (字段名归一)         │
                                │   ├─ validate(schema, args)  Issue 列表   │
                                │   ├─ if issues:                          │
                                │   │    deep_copy(args)                   │
                                │   │    for issue: shape_fix 按序尝试       │
                                │   │      ② stringified_array ─┐           │
                                │   │      ③ bare_value_wrap    ├ 严禁调换   │
                                │   │      ④ empty_object_ph   │           │
                                │   │      ⑤ coerce_bool        │           │
                                │   │      ⑥ coerce_int         │           │
                                │   ├─ revalidate → 仍 fail → ok=False     │
                                │   ├─ path_clean (md_link_leak 兜底)      │
                                │   └─ relational_defaults (注意)          │
                                │      返回 (args, ok, notes)              │
                                └──────────────────────────────────────────┘
                                       │              │           │
                                       │ ok=True      │ ok=False  │ notes
                                       ▼              ▼           ▼
   loop.py:95 ──────────────────┐                                       │
   safe_parse_args(raw_args)    │                                       │
   ├─ ok: continue ─────────────┤                                       │
   └─ err: tool_call=bad_json ──┘                                       │
                                                                        │
   BaseHandler.dispatch (插入修复管线):                                  │
   ┌──────────────────────────────────────────────────────────────────┐│
   │  if hasattr(self, method_name):                                  ││
   │      args, ok, notes = repair_tool_input(model, tool, args) ◀────┘│
   │      if not ok:                                                  │
   │          yield notes (透明打印)                                   │
   │          return StepOutcome(None, next_prompt=notes, ...)         │
   │      for n in notes: yield n (透明打印)                          │
   │      args['_index']=i; args['_tool_num']=n                      │
   │      ret = yield from do_*(args, response)                       │
   │      挂附 "注意" 提示到 ret.data (dict/str)                       │
   │      return ret                                                  │
   └──────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                          _hook('tool_repair', ctx)  每次修复 +1
                                       │
                                       ▼
                          REPAIR_STATS: Counter[(model, tool, kind)]
                                       │
                                       ▼
                          .tau/repair_telemetry.jsonl (落盘)
                                       │
                                       ▼
                          tau doctor  命令读取打印矩阵
```

**接入面**：仅 `BaseHandler.dispatch` 内部插入一行 `repair_tool_input` 调用 + 4 行附注/yield 处理；外部签名零变化。

---

## 3. 文件清单

| 操作 | 路径 | 职责 |
|---|---|---|
| **新建** | `core/agent/tool_repair.py` | schema 推导 + validate + shape_fix + path_clean + relational_defaults + telemetry |
| **修改** | `core/agent/loop.py` | L95 用 `safe_parse_args` 替代裸 `json.loads`（失败合成 `bad_json` 工具调用）；`BaseHandler.dispatch` 入口插入修复调用 + 未知工具近似匹配 + 透明 notes 打印 |
| **修改** | `core/agent/handler.py` | `_get_abs_path` 加 `..` 逃逸检查（返回 `None` 标志越界）；`do_file_read/write/patch` 调用点把 `None` 翻译为可重试 StepOutcome；L117 / L172 / L75 / L93 4 处去掉 `[Error]` 前缀并改写文案 |
| **新建** | `tau_cli/commands/doctor.py` | `tau doctor` 命令：读取 `REPAIR_STATS` 内存计数器（fallback 读 `.tau/repair_telemetry.jsonl`）打印 `model × tool × repair_kind` 矩阵 + 总修复次数 + 最近 N 条 |
| **新建** | `tests/test_tool_repair.py` | 12 个用例：safe_parse_args (2) / opaque 不误伤 (1) / 修复顺序 (1) / 裸值包装 (1) / null 剔除 (1) / 空对象占位 (1) / 布尔反转 (1) / 链接泄露 (1) / 关系默认值 (1) / 快路径零拷贝 (1) / 别名 falsy 值 (1) |
| **修改** | `tau_cli/cli.py` | `COMMANDS` 字典加 `"doctor": doctor_cmd.COMMAND` + 分发分支加 `if cmd == "doctor": doctor_cmd.run(extra or None); return` |

---

## 4. `core/agent/tool_repair.py` 设计要点

### 4.1 schema 自动推导

```python
import inspect
from typing import get_type_hints

_OPAQUE_HINT_NAMES = frozenset({
    "code", "script", "content", "old_content", "new_content",
    "key_info", "prompt", "question",
})

_PATH_HINT_NAMES = frozenset({
    "path", "save_to_file",
})

def _infer_field_schema(name: str, param: inspect.Parameter) -> dict:
    spec: dict = {}
    # 类型注解优先
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
    else:
        # 退化到默认值类型
        if param.default is not inspect.Parameter.empty:
            spec["type"] = _py_type_to_schema_type(type(param.default))
        else:
            spec["type"] = "string"  # 最保守
    # 启发式：opaque
    if name in _OPAQUE_HINT_NAMES:
        spec["opaque"] = True
    # 启发式：path
    if name in _PATH_HINT_NAMES:
        spec["type"] = "path"
    # 启发式：aliases（仅 switch_tab_id 已知别名 tab_id）
    if name == "switch_tab_id":
        spec["aliases"] = ["tab_id"]
    return spec

def derive_schema(handler_cls) -> dict[str, dict]:
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

SCHEMAS: dict[str, dict] = {}  # 启动时由 init_schemas(handler_cls) 填充
def init_schemas(handler_cls) -> None:
    """由 tau_cli/commands/run.py 或 runtime.main() 启动时调用一次。"""
    global SCHEMAS
    SCHEMAS = derive_schema(handler_cls)
```

### 4.2 safe_parse_args（P0 修复）

```python
def safe_parse_args(raw: str) -> tuple[dict | None, str | None]:
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

### 4.3 修复顺序（**严禁调换**）

```python
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

def _fix_coerce_bool(v, t):                              # ⑤
    if t == "boolean" and isinstance(v, str):
        low = v.strip().lower()
        if low in ("true", "1", "yes"): return True
        if low in ("false", "0", "no"): return False
    return _NO_FIX

def _fix_coerce_int(v, t):                              # ⑥
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

### 4.4 validate（递归带路径 Issue）

不展开全文（与方案一致）：`_TYPE_CHECKS` 字典型 + 短路的 `Issue(path, expected, actual, value)` 累加；opaque 字段永不校验；required missing 不尝试修复（直接进入 ok=False 返回路径）。

### 4.5 路径清洗

```python
_MD_LINK = re.compile(r"^\[([^\]]+)\]\((?:[a-z]+://)?([^)]+)\)$")

def clean_path_string(v: str) -> str:
    s = v.strip().strip("`")
    m = _MD_LINK.match(s)
    if m and m.group(1).strip() == m.group(2).strip():
        return m.group(1).strip()
    return s
```

仅处理退化 markdown 自动链接；真链接不动。

### 4.6 关系不变量（注意：file_read 真实参数是 `start/count/keyword/show_linenos`，不是 `offset/limit`）

```python
DEFAULT_READ_COUNT = 200
DEFAULT_KEYWORD_WINDOW = 50

def apply_relational_defaults(tool_name: str, args: dict) -> str | None:
    if tool_name == "file_read":
        has_start = "start" in args
        has_count = "count" in args
        if has_count and not has_start:
            args["start"] = 1
            return (f"注意：start 未提供，已默认为 1。"
                    f"如需从其他行开始，请同时提供 start 与 count 重试。")
        if has_start and not has_count:
            args["count"] = DEFAULT_READ_COUNT
            return (f"注意：count 未提供，已默认为 {DEFAULT_READ_COUNT} 行。"
                    f"如需读取更多或更少，请同时提供 start 与 count 重试。")
    return None
```

### 4.7 遥测

```python
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

### 4.8 主入口 `repair_tool_input`

```python
def repair_tool_input(model_id: str, tool_name: str, raw_args: dict):
    schema = SCHEMAS.get(tool_name)
    if schema is None or not isinstance(raw_args, dict):
        return raw_args, True, []                        # 未注册工具不拦截

    # 别名归一（不用 or：0 也是合法值）
    for field, spec in schema.get("properties", {}).items():
        if field not in raw_args:
            for alias in spec.get("aliases", []):
                if alias in raw_args:
                    raw_args[field] = raw_args.pop(alias)
                    _record(model_id, tool_name, "alias_normalize", [field]); break

    issues = validate(schema, raw_args)
    if not issues:
        args = raw_args                                  # 快路径：零拷贝、永不触碰
    else:
        args = json.loads(json.dumps(raw_args))          # 深拷贝，原始输入留证
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
            notes = [i.human() + "。请修正后重试。" for i in remaining]
            return args, False, notes

    # 路径字段清洗（按 schema type=path 精确触发）
    _walk_paths(schema, args, [])

    note = apply_relational_defaults(tool_name, args)
    notes = []
    if args is not raw_args:
        notes.append("[工具输入已修复]")
    if note:
        notes.append(note)
    return args, True, notes
```

### 4.9 不 raise 契约

`repair_tool_input` 的返回值 `(args, ok, notes)` 中 `ok=False` 时 notes 是给模型的可读重试提示（不含 `[Error]` 前缀）。`BaseHandler.dispatch` 收到 `ok=False` 时：
1. `yield notes` 透明打印给用户看
2. 返回 `StepOutcome(None, next_prompt='；'.join(notes), should_exit=False)`

绝不 raise —— `BaseHandler.dispatch` 是生成器，raise 会炸 `agent_runner_loop`。

---

## 5. `core/agent/loop.py` 接入代码

### 5.1 L95 `json.loads` 替换

**Before**（loop.py:95）：
```python
tool_calls = [{'tool_name': tc.function.name, 'args': json.loads(tc.function.arguments), 'id': tc.id}
              for tc in response.tool_calls]
```

**After**：
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
if not tool_calls:
    tool_calls = [{'tool_name': 'no_tool', 'args': {}}]
```

**不破坏**：现有 `bad_json` 工具分支（loop.py:27 + handler.py:117/172 都有 `bad_json` 处理路径）的 `StepOutcome(next_prompt=args.get('msg', 'bad_json'), should_exit=False)` 仍能消化此调用。

### 5.2 `BaseHandler.dispatch` 修复管线接入

**Before**（loop.py:19-30）：
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

**After**：
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
        # 关系默认值产生的附注（"注意：..."）透明 yield；最后挂到 ret.data
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


def _resolve_model(handler):
    try:
        return getattr(getattr(getattr(handler, 'parent', None), 'llmclient', None), 'model', '') or ''
    except Exception:
        return ''
```

**关键不变量保留**：
- `next_prompt.startswith('未知工具')` → `client.last_tools = ''` 的工具描述重发机制仍然命中（msg 以"未知工具"开头）
- `_hook('tool_before'/'tool_after', locals())` 字符串钩子协议原样
- `try_call_generator` 把 `do_*` 生成器扁平化逻辑不动

### 5.3 schema 初始化

`init_schemas(TauHandler)` 在 runtime 启动时调用一次（`core/agent/runtime.py` 的 `main()` 入口处）。在 worktree 端具体行号待 plan 阶段核实，但语义：进程启动时调一次，进程内全局复用。

---

## 6. `core/agent/handler.py` 4 处错误分级 + `_get_abs_path` 改造

### 6.1 `_get_abs_path` 加 `..` 逃逸检查

**Before**（handler.py:41-43）：
```python
def _get_abs_path(self, path):
    if not path: return ""
    return os.path.abspath(os.path.join(self.cwd, path))
```

**After**：
```python
def _get_abs_path(self, path):
    if not path: return ""
    abs_path = os.path.abspath(os.path.join(self.cwd, path))
    cwd_abs = os.path.abspath(self.cwd)
    try:
        if os.path.commonpath([abs_path, cwd_abs]) != cwd_abs:
            return None                                    # 越界标志
    except ValueError:
        # 不同驱动器（Windows）或路径非法
        return None
    return abs_path
```

### 6.2 `do_file_read/write/patch` 调用点翻译 None

每处 `_get_abs_path(args.get("path", ""))` 调用后紧跟：
```python
if path is None:
    yield f"[Status] ❌ 路径越界：参数 path 解析后跳出了工作目录 {self.cwd}，请提供工作目录内的相对路径后重试。\n"
    return StepOutcome({"status": "error", "msg": "路径越界，..."}, next_prompt="\n")
```

### 6.3 4 处可重试错误去 `[Error]` 前缀

| 行号 | 现 | 改 |
|---|---|---|
| L117 | `StepOutcome("[Error] Code missing. Must use reply code block or 'script' arg.", next_prompt="\n")` | `StepOutcome("未收到代码。请把代码放入 ```python 代码块或 code 参数后重试。", next_prompt="\n")` |
| L172 | `StepOutcome("[Error] Script missing. Use ```javascript block or 'script' arg.", next_prompt="\n")` | `StepOutcome("未收到脚本。请把脚本放入 ```javascript 代码块或 script 参数后重试。", next_prompt="\n")` |
| L75 | `StepOutcome({"status": "error", "msg": "No content found. Blank is not supported. Put content inside ...</file_content> tags in your reply body before call file_write."}, next_prompt="\n")` | `StepOutcome({"status": "error", "msg": "未找到要写入的内容。请将内容放入 <file_content>...</file_content> 标签内，或作为 content 参数传入后重试。"}, next_prompt="\n")` |
| L93 | `StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")` 引用展开失败 | 把 `str(e)` 包装为 `f"引用展开失败：{e}。请检查 @path 引用是否指向存在的文件后重试。"` |

**不动**：`[Status] ❌` 环境错误前缀（这些是真错误）、`[Warn]` / `[Info]` / `[System]` 前缀。

---

## 7. `tau_cli/commands/doctor.py`

```python
"""tau doctor — 工具输入修复遥测查看器"""
import sys, json
from collections import Counter
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
    # 1) 优先读内存（仅当 Tau 进程在跑时可用）
    from core.agent import tool_repair
    stats = dict(tool_repair.REPAIR_STATS)
    # 2) 内存为空时 fallback 读 jsonl
    if not stats:
        records = _read_fallback_jsonl()
        for r in records:
            stats[(r.get("model", ""), r.get("tool", ""), r.get("repair", ""))] = \
                stats.get((r.get("model", ""), r.get("tool", ""), r.get("repair", "")), 0) + 1
    if not stats:
        print("🟢 暂无修复记录（健康）")
        return
    # 3) 按 model 聚合打印
    by_model: dict[str, Counter] = {}
    for (model, tool, kind), n in stats.items():
        by_model.setdefault(model or "<unknown>", Counter())[(tool, kind)] += n
    print(f"🔧 工具输入修复遥测 — 总修复次数: {sum(stats.values())}")
    for model, ctr in sorted(by_model.items()):
        print(f"\n## Model: {model}")
        print(f"  {'tool':<25} {'repair_kind':<22} {'count':>5}")
        for (tool, kind), n in sorted(ctr.items(), key=lambda x: -x[1]):
            print(f"  {tool:<25} {kind:<22} {n:>5}")
    # 4) 最近 N 条原始记录
    records = _read_fallback_jsonl(20)
    if records:
        print(f"\n最近 {len(records)} 条落盘记录（.tau/repair_telemetry.jsonl）：")
        for r in records[-10:]:
            print(f"  {r.get('ts', 0):.0f}  {r.get('tool','?'):<20} {r.get('repair','?'):<22} path={r.get('path','?')}")
```

`tau_cli/cli.py` 的 `COMMANDS` 字典与 dispatch 分发同步加 `"doctor"` 项（与 `status` 同模式）。

---

## 8. 测试计划 `tests/test_tool_repair.py`

按方案 §五 12 个用例，每条一个 `def test_*`：

| # | 用例 | 断言要点 |
|---|---|---|
| 1 | `test_safe_parse_args_ok` | `safe_parse_args('{"a":1}')` → `({"a":1}, None)` |
| 2 | `test_safe_parse_args_lenient` | `safe_parse_args('{"a":1,}')` → `({"a":1}, 'lenient_json')`；`safe_parse_args('not json')` → `(None, err)` |
| 3 | `test_opaque_content_preserved` | `repair_tool_input('', 'file_write', {'path':'a', 'content':'["a","b"]'})` → `args['content'] == '["a","b"]'` 不被解析为数组 |
| 4 | `test_stringified_array_before_wrap` | `repair_tool_input('', 'ask_user', {'question':'q', 'candidates':'["A","B"]'})` → `args['candidates'] == ['A','B']`（两元素，非单元素包了字符串的列表） |
| 5 | `test_bare_value_wrap` | `candidates='A'` → `['A']` |
| 6 | `test_null_optional_dropped` | `timeout=None`（opaque 之外）→ 字段被删 |
| 7 | `test_empty_object_placeholder` | `candidates={}` → `[]` |
| 8 | `test_coerce_bool` | `tabs_only='false'` → `False`（非 truthy 字符串） |
| 9 | `test_md_link_leak` | `path='[a.txt](a.txt)'` → `'a.txt'`；`path='[doc](https://x.com/y)'` → 原样 |
| 10 | `test_relational_defaults_file_read` | `file_read` 只传 `count=100` → 补 `start=1`，附注以"注意"开头无 `[Error]` |
| 11 | `test_fast_path_zero_copy` | 合法输入 → 返回 `args is raw_args`（同一引用，未拷贝） |
| 12 | `test_alias_falsy_value` | `web_execute_js` 的 `tab_id=0` → 归一为 `switch_tab_id=0`（不被吞掉） |

**fixture**：测试文件 import `core.agent.tool_repair`，首次调用前 `init_schemas(TauHandler)`。每个用例独立，互不污染 `REPAIR_STATS`（用 pytest fixture 清零）。

**不测**：`dispatch` 接入（属集成测试，留 smoke 阶段手动验）；`_get_abs_path` 路径逃逸（用 `tests/test_path_safety.py` 单独文件更聚焦，本次先与 handler.py 同 commit 一起改但不在 tool_repair 测试套件里）。

---

## 9. 错误处理总览

| 失败场景 | 行为 |
|---|---|
| 畸形 JSON（`safe_parse_args` 二次宽松仍失败） | loop.py 合成 `bad_json` 工具调用，`dispatch` 走 `bad_json` 分支返回 `StepOutcome(next_prompt=msg)` |
| validate 全部通过 | 快路径：`args is raw_args`，零开销 |
| validate 失败但 shape_fix 能修 | 修完 revalidate 通过 → `ok=True`，notes 含 `[工具输入已修复]` |
| validate 失败 shape_fix 修不了 | `ok=False`，notes 是每条 issue 的 human() + "请修正后重试。" 经 `next_prompt` 回传模型自然重试 |
| `_get_abs_path` 返回 None | `do_file_*` 调用点翻译为 `StepOutcome({"status":"error", ...}, next_prompt="\n")`，可重试 |
| `_hook('tool_repair', ...)` 触发 ImportError | 静默跳过，遥测不影响主流程 |
| `.tau/repair_telemetry.jsonl` 写入 OSError | 静默跳过，不影响主流程 |
| `inspect.signature(do_xxx)` 失败（极少见） | `derive_schema` 跳过该方法，对应工具不注册 schema，`repair_tool_input` 返回 `(raw_args, True, [])` 不拦截 |
| `difflib.get_close_matches` 未知工具无近似匹配 | fallback 到列出全部 `do_*` 工具名 |

**核心不变量**：任何失败路径都不 raise，全部走 `StepOutcome(next_prompt=...)` 回传；生成器协议不被破坏。

---

## 10. 实施范围与行数估算

| 文件 | 操作 | 行数 |
|---|---|---|
| `core/agent/tool_repair.py` | 新建 | ~280 |
| `core/agent/loop.py` | 修改 L19-30 + L95 | ~50 |
| `core/agent/handler.py` | 修改 `_get_abs_path` + 4 处错误分级 + 3 处 None 翻译 | ~60 |
| `tau_cli/commands/doctor.py` | 新建 | ~60 |
| `tau_cli/cli.py` | 修改 COMMANDS + 分发 | ~10 |
| `tests/test_tool_repair.py` | 新建 | ~180 |
| **总计** | | **~640 行** |

比方案原文（550 行）多 ~90 行，主因：
- schema 从 `do_*` 推导比手写多 50 行（`_infer_field_schema` + `derive_schema` + `init_schemas`）
- `tau doctor` 命令真实落地（不只占位）多 40 行
- 路径逃逸 3 处调用点 None 翻译多 15 行（每点 ~5 行）

符合"外科手术式改动"原则：不动顶层结构、新功能只增实现、dispatch 单点接入。

---

## 11. 实施顺序（先 plan 后执行）

1. **Task 1** 建 `core/agent/tool_repair.py` 骨架（safe_parse_args + 推导 schema + init_schemas）
2. **Task 2** 写 validate + shape_fix + path_clean + relational_defaults + 主入口 repair_tool_input
3. **Task 3** 加遥测（REPAIR_STATS + jsonl + _hook）
4. **Task 4** `loop.py` L95 用 safe_parse_args + dispatch 接 repair_tool_input + 未知工具近似匹配
5. **Task 5** `handler.py` `_get_abs_path` 逃逸检查 + 调用点 None 翻译
6. **Task 6** `handler.py` 4 处 `[Error]` 前缀改写
7. **Task 7** `tau_cli/commands/doctor.py` 新建 + cli.py 注册
8. **Task 8** `tests/test_tool_repair.py` 12 用例
9. **Task 9** 跑全量测试 + 手动 smoke（`python -c "from core.agent.handler import TauHandler; from core.agent.tool_repair import init_schemas; init_schemas(TauHandler)"`）

每步独立 commit，commit message 按已有 PR 风格（`feat/refactor/fix/test/chore`）。

---

## 12. 风险与回滚

| 风险 | 缓解 |
|---|---|
| `inspect.signature` 在某些边界（`*args` / `**kwargs` / 装饰器包装）推断出错 | `derive_schema` 对 signature 失败 try/except 跳过该方法；fallback 到无拦截 |
| 启发式 opaque 漏判（某新工具字段名字不含 `code/script/content` 但本质是 opaque） | 字段若非启发式命中，仍会被 `_fix_stringified_array` 等尝试 —— 但 validate 阶段会放过（因为启发式未标 opaque）；最坏情况：用户传入 `["a","b"]` 被解析为数组。**已知边界，本轮接受**，下一轮可加 `@tool_opaque` 装饰器补充 |
| dispatch 修复调用增加延迟 | 快路径零拷贝 + 不命中 validate 时无任何额外调用；最坏路径（深拷贝 + validate + 多次 fix）< 1ms |
| `.tau/repair_telemetry.jsonl` 无限增长 | `.gitignore` 已忽略；不需清理；如需可加最大行数截断（不在本轮范围） |
| `dispatch` 改后破坏现有 hook 协议 | `_hook('tool_before'/'tool_after', locals())` 原样保留，仅在 hook 之间插入修复调用 |
| `tau_cli` 命令名 `doctor` 与未来 `tau doctor` 冲突 | 先 `tau_cli list` 确认无冲突（本轮确认） |

**回滚策略**：每步独立 commit，revert 单个 commit 即回滚该步骤；最坏情况 revert 全部 9 个 commit 回到本 spec 之前状态。

---

## 13. 验收标准

- [ ] `tests/test_tool_repair.py` 12 个用例全绿
- [ ] `tests/test_core_agent_layout.py` 现有用例全绿（不破坏结构）
- [ ] `pytest tests/` 全绿（除 daily_report 等不相关）
- [ ] `python -c "from core.agent.tool_repair import init_schemas, repair_tool_input; from core.agent.handler import TauHandler; init_schemas(TauHandler); print(repair_tool_input('', 'file_read', {'path':'a'})[0])"` 不报错且输出 `{'path': 'a'}`
- [ ] `python -m tau_cli doctor` 输出"暂无修复记录（健康）"（全新启动时）
- [ ] `loop.py` L95 后的代码与原行为一致（除 bad_json 合成路径）
- [ ] `handler.py` 4 处文案改写无 `[Error]` 前缀，可重试味道
- [ ] 路径逃逸：用 `path="../../../etc/passwd"` 调 `file_read` 收到可重试错误而非读 /etc/passwd