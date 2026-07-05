# tool_repair schema 注入化设计

- **日期**：2026-07-05
- **方向**：core/agent 健壮性 / 契约硬化
- **状态**：已与用户确认设计，待写实现计划
- **关联 commit**：`c022438`（bootstrap 时初始化 tool_repair schema）、`7e24bb4`（tool_repair 13 用例）、`d341dc1`（final review follow-ups）

## 背景与问题陈述

`tool_repair` 通过 AST 扫描 `TauHandler` 的 `do_*` 方法，推导出每个工具的参数 schema，用于在 dispatch 前校验并定点修复 LLM 产出的畸形工具输入（裸值包装、字符串化数组、null 可选字段、markdown 链接泄漏等）。

当前 schema 的承载方式是**模块级可变全局**：

```python
# core/agent/tool_repair.py:21
SCHEMAS: dict[str, dict] = {}
```

其正确性隐式依赖一条口头契约：**「`bootstrap()` 必须先跑 `init_schemas(TauHandler)`」**（[runtime.py:79-81](../../core/agent/runtime.py)）。

这条隐式契约带来一个静默失效陷阱：

- `repair_tool_input`（[tool_repair.py:365-368](../../core/agent/tool_repair.py)）在 `SCHEMAS.get(tool_name)` 为空时，直接 `return raw_args, True, []`——**不崩，但 repair 能力消失**。
- 任何绕过 `bootstrap()` 的入口（独立测试、subagent、`tau run` 的某些早期路径、未来新增入口）会让 repair 静默 no-op，且调用方无从感知。
- 这违反 CONTRIBUTING 原则「约束写进代码」（依赖口头约定而非结构保证）与「let it crash 按失败半径」（静默失效比崩更难定位）。

最近 commit `c022438` 已经触及这条依赖（把 init_schemas 挪进 bootstrap），说明它已在关注面上。本设计把 schema 来源从「启动时副作用」改为「import handler 即自举 + dispatch 显式注入」，彻底消除主路径对 bootstrap 的依赖。

## 目标与非目标

**目标**：
1. 生产主路径（`BaseHandler.dispatch → repair_tool_input`）的 schema 来源**不依赖 `bootstrap()`**。
2. 现有 13 个 tool_repair 用例与全部 layout 测试**零改动**通过。
3. 改动半径最小（外科手术式，符合 CONTRIBUTING「改动半径小」「更多功能→更少代码」）。

**非目标**（明确排除）：
- 不删除模块级 `SCHEMAS` 全局（保留为测试 fixture 的回退源，使现有 13 用例零改动；生产主路径不再读它）。
- 不重构 `repair_tool_input` 的内部修复逻辑（校验器、形状修复顺序、opaque 守护等均不动）。
- 不改变 `init_schemas` 的公开签名。
- 不处理方向 ①（`_init_streams` 重复）与方向 ③（handler 拆分）——它们是独立后续项。

## 现状分析

### 调用点（grep 实测，共 2+2 处）

| 符号 | 调用点 | 用途 |
|---|---|---|
| `repair_tool_input` | [loop.py:31](../../core/agent/handler.py)（dispatch 内，生产） | 主路径 |
| `repair_tool_input` | [test_tool_repair.py:23](../../tests/test_tool_repair.py)（`_repair` helper） | 测试 |
| `init_schemas` | [runtime.py:81](../../core/agent/runtime.py)（bootstrap） | 生产初始化 |
| `init_schemas` | [test_tool_repair.py:10](../../tests/test_tool_repair.py)（autouse fixture） | 测试 setup |

### 测试浮现的硬约束

- **`test_loop_no_upper_deps`**（[test_core_agent_layout.py:26-31](../../tests/test_core_agent_layout.py)）：loop.py 源码不得出现 `from .handler` / `import core.agent.handler`。→ dispatch 取 schemas 只能走 `self` 反射或参数，**不能在 loop.py 顶部 import TauHandler**。
- **`test_fast_path_zero_copy`**（[test_tool_repair.py:103-107](../../tests/test_tool_repair.py)）：合法输入 `args is raw`（快路径零拷贝）。→ schema 查询路径不能引入额外拷贝。
- **fixture 模式**：autouse fixture 调 `init_schemas(TauHandler)` 填全局，`_repair` 不传 schemas 走全局回退。→ `repair_tool_input` 新增参数必须可选且默认走原回退路径。

## 设计方案：三层机制

### 核心：「handler 自举 + dispatch 注入 + 全局回退」

**层 1 — handler 自举**：在 `core/agent/handler.py` 末尾加一行
`TauHandler.TOOL_SCHEMAS = derive_schema(TauHandler)`。任何 `import TauHandler`（所有运行路径必经）即自动算好 schemas 挂到类属性。

- 循环依赖安全：`handler.py → tool_repair` 单向（已存在），tool_repair 顶部不 import handler。
- `derive_schema` 内部对每个 `do_*` 方法的 AST 解析已 catch `OSError/SyntaxError/TypeError/IndentationError` 返回 `{}`（[tool_repair.py:45](../../core/agent/tool_repair.py)），不会抛，import 期安全。
- 边际成本：handler.py 本就 import code_run/file_io/web 等重模块，多一次 AST 扫描可忽略。

**层 2 — dispatch 注入**：[loop.py:31](../../core/agent/handler.py) dispatch 改为 `schemas = getattr(self, 'TOOL_SCHEMAS', None)` 再传给 `repair_tool_input(..., schemas)`。

- loop.py 只用 getattr 反射，不 import handler，满足 `test_loop_no_upper_deps`。
- `BaseHandler` 自身不要求有 `TOOL_SCHEMAS`；非 TauHandler 子类走 getattr 兜底 None → 回退全局。

**层 3 — 全局回退**：`repair_tool_input` 签名加 `schemas: dict | None = None`；为 None 时回退模块级 `SCHEMAS`。

- 现有测试 `_repair(model, tool, args)` 不传 schemas → 走回退 → 零改动。
- `init_schemas` 仍填充模块级 SCHEMAS（保留为测试 fixture 的回退源），且额外注入 `handler_cls.TOOL_SCHEMAS`（幂等，与层 1 自举值一致）。

### 数据流

```
生产主路径（不依赖 bootstrap）:
  import TauHandler  →  handler.py 末尾自举  →  TauHandler.TOOL_SCHEMAS 就位
  dispatch(self, ...)
    schemas = getattr(self, 'TOOL_SCHEMAS', None)   # 反射，不 import handler
    repair_tool_input(model, tool, args, schemas)    # 显式注入
      schema = schemas.get(tool_name)                # 命中 → 修复

直调路径（测试 fixture / 未来扩展，走全局回退）:
  repair_tool_input(model, tool, args)               # schemas=None
    schema = SCHEMAS.get(tool_name)                  # 回退全局
```

## 逐文件改动明细

### ① `core/agent/tool_repair.py` — 2 处

**`init_schemas`（[line 140-143](../../core/agent/tool_repair.py)）** — 注入类属性 + 合并 derive 调用：
```python
def init_schemas(handler_cls) -> None:
    """填充进程级 SCHEMAS，并注入 handler_cls.TOOL_SCHEMAS（dispatch 注入路径用）。"""
    derived = derive_schema(handler_cls)
    SCHEMAS.clear(); SCHEMAS.update(derived)
    handler_cls.TOOL_SCHEMAS = dict(derived)   # 新增
```

**`repair_tool_input`（[line 365-366](../../core/agent/tool_repair.py)）** — 新增可选参数 + 回退：
```python
def repair_tool_input(model_id: str, tool_name: str, raw_args: dict, schemas: dict | None = None):
    src = schemas if schemas is not None else SCHEMAS
    schema = src.get(tool_name)
```

### ② `core/agent/handler.py` — 2 处

**顶部 import 区**（[line 22](../../core/agent/handler.py) 附近，`from ..paths import MEMORY` 之后）补：
```python
from .tool_repair import derive_schema
```

**文件末尾**（TauHandler 类定义之后）加自举：
```python
TauHandler.TOOL_SCHEMAS = derive_schema(TauHandler)
```

### ③ `core/agent/loop.py` — 1 处

**`dispatch` 内（[line 29-31](../../core/agent/handler.py)）** — 反射取 schemas 注入：
```python
from .tool_repair import repair_tool_input
model = _resolve_model(self)
schemas = getattr(self, 'TOOL_SCHEMAS', None)          # 新增
args, ok, notes = repair_tool_input(model, tool_name, args, schemas)   # 末尾加 schemas
```
> 局部 `from .tool_repair import ...` 已存在，仅延伸。getattr 反射不违反 `test_loop_no_upper_deps`。

### ④ `core/agent/runtime.py` — 仅 docstring

[bootstrap docstring line 67-69](../../core/agent/runtime.py) 补一句：`init_schemas` 现在幂等且同时注入类属性，handler import 时已自举，本调用保留为进程级 SCHEMAS 的 source of truth（供测试 fixture 回退）。**代码无改动**——[line 81](../../core/agent/runtime.py) 行为等价。

## 不变量（设计必须保持）

1. **快路径零拷贝**：合法输入仍 `args is raw`。schemas 仅用于 `.get(tool_name)` 查询，不影响 args 别名与零拷贝语义。
2. **失败半径**：`repair_tool_input` 在 schema 缺失时仍 no-op 不崩（repair 是优化层，失败半径=0，静默放过合理）。本设计不改变这点，只是让 schema 缺失在生产主路径几乎不可能发生。
3. **layout 不变量**：loop.py 不 import handler/runtime；`TauHandler.__module__ == "core.agent.handler"`；`Tau.__module__ == "core.agent.runtime"`；shim 仍指向新实现。
4. **向后兼容**：`repair_tool_input`/`init_schemas` 旧签名仍可调；现有调用点（2+2 处）行为等价。

## 测试策略

### 回归（零改动，必须全绿）

- **[tests/test_tool_repair.py](../../tests/test_tool_repair.py) 13 用例**：autouse fixture 填全局、`_repair` 走回退——签名兼容，无需改动。
- **[tests/test_core_agent_layout.py](../../tests/test_core_agent_layout.py) 全部**：`test_loop_no_upper_deps` 守护 loop.py 不 import handler（getattr 不违反）；其余结构断言不受影响。

### 新增守护：`tests/test_tool_repair_injection.py`（新文件，无 autouse fixture）

```python
"""锁死 tool_repair 的注入路径：schema 来源不依赖 bootstrap/init_schemas。"""

def test_handler_self_bootstrap_schemas():
    """import TauHandler 即自动推导 TOOL_SCHEMAS，无需 init_schemas/bootstrap。"""
    from core.agent.handler import TauHandler
    schemas = getattr(TauHandler, 'TOOL_SCHEMAS', None)
    assert isinstance(schemas, dict) and schemas
    assert 'file_read' in schemas and 'code_run' in schemas

def test_repair_injection_independent_of_global():
    """显式 schemas 参数优先；全局空时注入路径仍修复、不注入则静默 no-op。"""
    from core.agent import tool_repair
    from core.agent.handler import TauHandler
    tool_repair.SCHEMAS.clear()                      # 模拟"未 bootstrap"
    schemas = tool_repair.derive_schema(TauHandler)
    # 注入路径 → 修复生效（bare_value_wrap）
    args, ok, _ = tool_repair.repair_tool_input(
        '', 'ask_user', {'question': 'q', 'candidates': 'A'}, schemas=schemas)
    assert ok and args['candidates'] == ['A']
    # 不注入且全局空 → 静默 no-op（schema 缺失，原样返回，不崩）
    args2, ok2, _ = tool_repair.repair_tool_input(
        '', 'ask_user', {'question': 'q', 'candidates': 'A'})
    assert ok2 and args2['candidates'] == 'A'        # 未被修复
```

### 不加的测试（YAGNI）

- dispatch 端到端 mock：要 mock client/response/生成器，重而收益低，留给 verify 阶段。
- 循环 import 守护：循环 import 会 import 期即崩，测试收集阶段自然暴露，无需显式断言。

## 验证计划（实现完成后）

新增单元测试锁契约；端到端用 verify skill 跑 before/after 对比：

1. **before**（当前代码）：临时注释 [runtime.py:81](../../core/agent/runtime.py) 的 `init_schemas` 调用 → `tau run` 触发一次带缺陷工具调用（如 `candidates: "A"` 裸值）→ 观察 dispatch 是否未修复（原样 `"A"`）。
2. **after**（本设计）：同样注释掉 bootstrap 的 init_schemas → 同样触发 → 观察是否仍修复为 `["A"]`（因 handler import 时已自举 TOOL_SCHEMAS）。
3. 恢复 runtime.py:81。

## 风险与回滚

| 风险 | 概率 | 缓解 |
|---|---|---|
| handler.py import-time 自举失败导致整包 import 崩 | 极低（`derive_schema` 内部已 catch AST 错误） | 13 用例 + layout 测试会在收集期暴露 |
| 循环 import | 无（tool_repair 不 import handler，单向） | 现有依赖方向已验证 |
| `getattr(self, 'TOOL_SCHEMAS', None)` 在非 TauHandler 子类返回 None | 设计预期（回退全局） | 非回归——BaseHandler 子类本就走全局路径 |
| 测试 fixture 与自举值漂移 | 无（`init_schemas` 重设类属性，值与自举一致） | fixture 幂等 |

**回滚**：改动集中在 3 文件 ~6 行，`git revert` 即可完整回滚；新增测试文件独立，可单独删除。
