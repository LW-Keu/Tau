# tool_repair schema 注入化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 tool_repair 的 schema 来源从「bootstrap 时填全局」改为「import handler 即自举类属性 + dispatch getattr 反射注入」，消除生产主路径对 bootstrap 的隐式依赖。

**Architecture:** 三层机制——① `repair_tool_input` 加可选 `schemas` 参数（None 回退全局）；② `handler.py` 末尾 import 时自举 `TauHandler.TOOL_SCHEMAS` + `init_schemas` 同步注入类属性；③ `loop.py` dispatch 用 `getattr(self, 'TOOL_SCHEMAS', None)` 注入。模块级 `SCHEMAS` 保留为测试 fixture 回退源。

**Tech Stack:** Python 3.10–3.13、pytest、uv、stdlib AST/inspect（已有）。

**Spec:** [docs/superpowers/specs/2026-07-05-tool-repair-schema-injection-design.md](../specs/2026-07-05-tool-repair-schema-injection-design.md)（commit `c2409f1`）

## Global Constraints

- **Python**: `requires-python = ">=3.10,<3.14"`（pyproject.toml），不得引入新依赖。
- **包管理**: uv，不用 pip/venv 直接装。
- **不变量 1（快路径零拷贝）**: 合法输入 `args is raw` 必须保持——schemas 仅用于 `.get(tool_name)` 查询，禁止在 repair 路径引入深拷贝。
- **不变量 2（layout）**: `loop.py` 源码不得出现 `from .handler` / `import core.agent.handler`（由 `tests/test_core_agent_layout.py::test_loop_no_upper_deps` 守护）；只能用 `getattr(self, ...)` 反射。
- **不变量 3（向后兼容）**: `repair_tool_input` / `init_schemas` 旧签名必须保持可调；现有 13 个 tool_repair 用例零改动通过。
- **不变量 4（失败半径）**: schema 缺失时 repair 静默 no-op 不崩（repair 是优化层）。
- **commit 规范**: message 形如 `<type>(agent): <subject>`，结尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`；只 `git add` 本任务显式列出的文件，**不要** `git add -A`（仓库有 untracked 的 `autonomous.pid` 等无关文件）。
- **测试运行**: 在仓库根用 `.venv` 跑 `python -m pytest <path> -v`。

---

## Task 1: `repair_tool_input` 加可选 `schemas` 参数（向后兼容回退）

**Files:**
- Modify: `core/agent/tool_repair.py:365-366`
- Test: `tests/test_tool_repair_injection.py`（新建）

**Interfaces:**
- Consumes: 已有的 `SCHEMAS` 模块全局（[tool_repair.py:21](../../core/agent/tool_repair.py)）。
- Produces: `repair_tool_input(model_id: str, tool_name: str, raw_args: dict, schemas: dict | None = None)` —— 新增第 4 参 `schemas`，为 `None` 时回退模块级 `SCHEMAS`，否则用传入的 dict。返回值契约不变：`(args, ok, notes)`。

- [ ] **Step 1: 写失败测试（新建测试文件）**

创建 `tests/test_tool_repair_injection.py`：

```python
"""锁死 tool_repair 的注入路径：schema 来源不依赖 bootstrap/init_schemas。"""


def test_repair_injection_independent_of_global():
    """显式 schemas 参数优先；全局空时注入路径仍修复、不注入则静默 no-op。"""
    from core.agent import tool_repair
    from core.agent.handler import TauHandler

    tool_repair.SCHEMAS.clear()                      # 模拟"未 bootstrap"
    schemas = tool_repair.derive_schema(TauHandler)
    # 注入路径 → 修复生效（bare_value_wrap: 'A' -> ['A']）
    args, ok, _ = tool_repair.repair_tool_input(
        '', 'ask_user', {'question': 'q', 'candidates': 'A'}, schemas=schemas)
    assert ok and args['candidates'] == ['A']
    # 不注入且全局空 → 静默 no-op（schema 缺失，原样返回，不崩）
    args2, ok2, _ = tool_repair.repair_tool_input(
        '', 'ask_user', {'question': 'q', 'candidates': 'A'})
    assert ok2 and args2['candidates'] == 'A'        # 未被修复
```

- [ ] **Step 2: 跑测试看失败**

```bash
python -m pytest tests/test_tool_repair_injection.py::test_repair_injection_independent_of_global -v
```
Expected: FAIL —— `repair_tool_input() got an unexpected keyword argument 'schemas'`（TypeError）。前半断言（注入路径）就过不去。

- [ ] **Step 3: 实现——改 `repair_tool_input` 签名 + 回退**

编辑 `core/agent/tool_repair.py:365-366`，把：

```python
def repair_tool_input(model_id: str, tool_name: str, raw_args: dict):
    schema = SCHEMAS.get(tool_name)
```

改为：

```python
def repair_tool_input(model_id: str, tool_name: str, raw_args: dict, schemas: dict | None = None):
    src = schemas if schemas is not None else SCHEMAS
    schema = src.get(tool_name)
```

- [ ] **Step 4: 跑新测试看通过**

```bash
python -m pytest tests/test_tool_repair_injection.py::test_repair_injection_independent_of_global -v
```
Expected: PASS。

- [ ] **Step 5: 回归——现有 13 用例零改动通过**

```bash
python -m pytest tests/test_tool_repair.py -v
```
Expected: 13 passed（fixture 调 `init_schemas` 填全局，`_repair` 不传 `schemas` 走回退，行为等价）。

- [ ] **Step 6: 提交**

```bash
git add core/agent/tool_repair.py tests/test_tool_repair_injection.py
git commit -m "$(cat <<'EOF'
refactor(agent): repair_tool_input 加 schemas 参数（向后兼容）

新增可选第 4 参 schemas，None 时回退模块级 SCHEMAS。为 dispatch 注入路径
铺路；现有调用点（含测试 fixture）零改动。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: handler 自举 + `init_schemas` 注入 `TOOL_SCHEMAS` 类属性

**Files:**
- Modify: `core/agent/tool_repair.py:140-143`（`init_schemas`）
- Modify: `core/agent/handler.py:24`（顶部 import 区）+ 文件末尾（自举行）
- Test: `tests/test_tool_repair_injection.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 `repair_tool_input(schemas=...)`；已有的 `derive_schema(handler_cls)`（[tool_repair.py:109](../../core/agent/tool_repair.py)）。
- Produces: `TauHandler.TOOL_SCHEMAS: dict`（类属性，import handler 时自举就位）；`init_schemas(handler_cls)` 副作用增加「设 `handler_cls.TOOL_SCHEMAS = dict(derived)`」。

- [ ] **Step 1: 写失败测试（追加到现有文件）**

在 `tests/test_tool_repair_injection.py` 末尾追加：

```python
def test_handler_self_bootstrap_schemas():
    """import TauHandler 即自动推导 TOOL_SCHEMAS，无需 init_schemas/bootstrap。"""
    from core.agent.handler import TauHandler

    schemas = getattr(TauHandler, 'TOOL_SCHEMAS', None)
    assert isinstance(schemas, dict) and schemas
    assert 'file_read' in schemas and 'code_run' in schemas
```

- [ ] **Step 2: 跑测试看失败**

```bash
python -m pytest tests/test_tool_repair_injection.py::test_handler_self_bootstrap_schemas -v
```
Expected: FAIL —— `getattr(TauHandler, 'TOOL_SCHEMAS', None)` 返回 `None`，`assert isinstance(None, dict)` 失败。

- [ ] **Step 3: 实现——handler.py 顶部加 import**

编辑 `core/agent/handler.py`，在第 24 行 `from ..paths import MEMORY` 之后插入一行：

```python
from .tool_repair import derive_schema
```

（插入后第 25 行，原 `from ..paths import MEMORY` 仍为第 24 行下方。）

- [ ] **Step 4: 实现——handler.py 末尾加自举**

在 `core/agent/handler.py` 文件**最末尾**（`TauHandler` 类之外，顶格无缩进，紧接 `turn_end_callback` 的 `return next_prompt` 之后空一行）追加：

```python


TauHandler.TOOL_SCHEMAS = derive_schema(TauHandler)
```

- [ ] **Step 5: 实现——init_schemas 同步注入类属性**

编辑 `core/agent/tool_repair.py:140-143`，把：

```python
def init_schemas(handler_cls) -> None:
    """由 runtime 启动入口调用一次，填充进程级 SCHEMAS。"""
    SCHEMAS.clear()
    SCHEMAS.update(derive_schema(handler_cls))
```

改为：

```python
def init_schemas(handler_cls) -> None:
    """填充进程级 SCHEMAS，并注入 handler_cls.TOOL_SCHEMAS（dispatch 注入路径用）。"""
    derived = derive_schema(handler_cls)
    SCHEMAS.clear()
    SCHEMAS.update(derived)
    handler_cls.TOOL_SCHEMAS = dict(derived)
```

- [ ] **Step 6: 跑新测试看通过**

```bash
python -m pytest tests/test_tool_repair_injection.py::test_handler_self_bootstrap_schemas -v
```
Expected: PASS。

- [ ] **Step 7: layout 回归——循环 import / 结构不变量**

```bash
python -m pytest tests/test_core_agent_layout.py -v
```
Expected: 全部 PASS。重点确认：
- `test_handler_module_importable`：handler import 不崩（无循环依赖）。
- `test_loop_no_upper_deps`：loop.py 仍未 import handler（本任务没动 loop.py）。

- [ ] **Step 8: 回归——现有 13 用例 + Task 1 测试**

```bash
python -m pytest tests/test_tool_repair.py tests/test_tool_repair_injection.py -v
```
Expected: 13 + 2 passed。

- [ ] **Step 9: 提交**

```bash
git add core/agent/handler.py core/agent/tool_repair.py tests/test_tool_repair_injection.py
git commit -m "$(cat <<'EOF'
feat(agent): handler 自举 TOOL_SCHEMAS + init_schemas 注入类属性

handler.py 末尾 import 时推导 TOOL_SCHEMAS 挂到类属性，消除对 bootstrap
的依赖；init_schemas 同步注入类属性（幂等）。循环依赖安全：单向
handler→tool_repair。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: dispatch 反射注入 + runtime docstring + 全量回归

**Files:**
- Modify: `core/agent/loop.py:29-31`（dispatch 内）
- Modify: `core/agent/runtime.py:67-69`（bootstrap docstring）
- Test: 无新增单元测试（依赖现有 layout 守护 + 端到端 verify）

**Interfaces:**
- Consumes: Task 1 的 `repair_tool_input(schemas=...)`；Task 2 的 `TauHandler.TOOL_SCHEMAS`。
- Produces: `BaseHandler.dispatch` 走注入路径——从 `self.TOOL_SCHEMAS` 读 schemas 传给 `repair_tool_input`。非 TauHandler 子类（无 `TOOL_SCHEMAS`）走 `getattr` 兜底 `None` → 回退全局。

- [ ] **Step 1: 实现——loop.py dispatch 注入**

编辑 `core/agent/loop.py:29-31`，把：

```python
            from .tool_repair import repair_tool_input
            model = _resolve_model(self)
            args, ok, notes = repair_tool_input(model, tool_name, args)
```

改为：

```python
            from .tool_repair import repair_tool_input
            model = _resolve_model(self)
            schemas = getattr(self, 'TOOL_SCHEMAS', None)
            args, ok, notes = repair_tool_input(model, tool_name, args, schemas)
```

> 注意：保持局部 `from .tool_repair import ...`（已在方法内），不要提升到模块顶部——`test_loop_no_upper_deps` 扫描源码字符串，顶部 import tool_repair 虽然允许（tool_repair 是下层），但保持原局部 import 风格更稳。

- [ ] **Step 2: 实现——runtime.py bootstrap docstring 更新**

编辑 `core/agent/runtime.py` 的 `bootstrap()` docstring（约第 67-69 行），把这段：

```python
      注：默认 tool schema 加载已迁到 Tau.__init__ 末尾，不在 bootstrap 副作用内。
```

改为：

```python
      注：默认 tool schema 加载已迁到 Tau.__init__ 末尾，不在 bootstrap 副作用内。
      注：tool_repair 的 SCHEMAS 现在由 handler.py import 时自举（TauHandler.TOOL_SCHEMAS），
          本处 init_schemas 调用幂等，保留为进程级 SCHEMAS 的 source of truth（测试 fixture 回退）。
```

**代码无改动**——`runtime.py:81` 的 `init_schemas(TauHandler)` 行为等价。

- [ ] **Step 3: layout 回归——loop.py 不 import handler**

```bash
python -m pytest tests/test_core_agent_layout.py::test_loop_no_upper_deps -v
```
Expected: PASS（`getattr` 反射不违反；loop.py 源码仍无 `from .handler` / `import core.agent.handler`）。

- [ ] **Step 4: 全量回归——所有相关测试**

```bash
python -m pytest tests/test_tool_repair.py tests/test_tool_repair_injection.py tests/test_core_agent_layout.py -v
```
Expected: 13 + 2 + layout 全部 passed。

- [ ] **Step 5: 端到端 before/after 验证（verify 范畴，确认注入路径生产可用）**

这一步证明「绕过 bootstrap，dispatch 仍修复」。用 Python 直接验证 `TauHandler.TOOL_SCHEMAS` 在 dispatch 路径就位，无需启动整个 runtime：

```bash
python -c "
from core.agent.handler import TauHandler
from core.agent import tool_repair
# 模拟'未 bootstrap'：清空进程级全局
tool_repair.SCHEMAS.clear()
# 验证 handler 自举的类属性仍存在（dispatch 会经 getattr 取到它）
assert isinstance(TauHandler.TOOL_SCHEMAS, dict) and 'ask_user' in TauHandler.TOOL_SCHEMAS
# 模拟 dispatch 注入路径
schemas = TauHandler.TOOL_SCHEMAS
args, ok, _ = tool_repair.repair_tool_input('', 'ask_user', {'question': 'q', 'candidates': 'A'}, schemas)
assert ok and args['candidates'] == ['A'], args
print('OK: 注入路径在未 bootstrap 时仍修复')
"
```
Expected: 打印 `OK: 注入路径在未 bootstrap 时仍修复`。

> 若想更彻底地驱动真实 dispatch，改用 `/verify` skill 跑 `tau run` 触发一次带缺陷工具调用（如让 LLM 调 `ask_user` 时 `candidates` 给裸值字符串），观察是否仍修复为列表——但 LLM 输出不确定，上述 Python 直验证已是确定性的契约证据。

- [ ] **Step 6: 提交**

```bash
git add core/agent/loop.py core/agent/runtime.py
git commit -m "$(cat <<'EOF'
feat(agent): dispatch 反射注入 TOOL_SCHEMAS，主路径脱钩 bootstrap

loop.py dispatch 用 getattr(self, 'TOOL_SCHEMAS', None) 取 schemas 传给
repair_tool_input。生产主路径不再依赖 bootstrap；runtime.py 仅更新 docstring。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

## 完成判定

三个 commit 全部落地后：
- `tests/test_tool_repair.py`（13）+ `tests/test_tool_repair_injection.py`（2）+ `tests/test_core_agent_layout.py` 全绿。
- `python -c "..."` 注入路径验证打印 OK。
- `git log --oneline -4` 看到 3 个新 commit（refactor / feat / feat）在 `c2409f1`（spec）之后。
