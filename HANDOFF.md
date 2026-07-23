# HANDOFF.md — 1.2 typed event 重构交接

> 写于 2026-07-22，会话续期第 1 步。
> 工作分支：`tau-v5.0.0`（领先 origin/tau-v5.0.0 共 9 个 commit，工作树干净）

---

## 一、我们在做什么

**1.2 typed event 重构** —— 砍掉 `agent_runner_loop` 的字符串契约，把 frontend（tui / web / common）从「解析渲染好的字符串」切到「消费结构化事件」，从而压住 apps/ 的膨胀。

**根因（写下来备忘，不要再争论）**：
`agent_runner_loop` yield 的是 `"\n\n**LLM Running (Turn N) ...**\n\n🛠️ Tool: `bash`  📥 args:\n````text\n…\n````\n"` 这种字符串，而非结构化事件。三处各写各的字符串解析：
- `apps/tui/app.py` 内联正则切 turn、抽 tool_use XML
- `apps/web/conductor.py` `_TURN_SPLIT_RE` / `_SUMMARY_RE` 抽摘要
- `apps/common/continue_cmd.py` 为复用 tui 的 fold_turns，把历史日志**逆向工程**成同形状字符串（注释里就这么写的：_format_tool_use + _format_tool_result）

字符串形状成了实时/回放/前端共享的隐式契约，**任何渲染改动都会同时撞三个地方**。

**前置（1.3）已完成** —— `handler` 通过 `HostContext` 协议（typing.Protocol）与 `Tau` 解耦（commits `ce62e5a` + `d0f62d7`）。handler 现在只依赖 `task_dir / verbose / _turn_end_hooks / history_snapshot()` 四个属性，可独立单测。这步让 1.2 的事件化重构不会把反向依赖 baked-in 到 agent_loop。

---

## 二、已经完成了什么（9 个 commit 链）

| commit | 阶段 | 改了什么 |
|---|---|---|
| `ce62e5a` | **1.3-A** | `tau_agent/handler.py` 引入 `HostContext` Protocol；签名改 `parent: HostContext` |
| `d0f62d7` | **1.3-B** | `taumain.py` 加 `history_snapshot()`，handler 改走协议；关掉 `inline_eval ns['parent']` 暗门 |
| `bdea7bb` | **1.2-0** | 新增 `src/tau_agent/events.py` —— 9 个 dataclass 事件（TurnStarted / AssistantTextChunk / AssistantTextDone / ToolCallStart / ToolOutputStart/Chunk/End / RawText / TurnEnded）+ `render_event(event, verbose)` + `render_events(events, verbose)` |
| `32c6ba5` | **1.2-1** | `agent_loop.py` 旧 `agent_runner_loop` 改名 `_agent_runner_loop_str_legacy`（保留作 golden ref），新增 `agent_runner_loop_events(...)` 直接 yield 事件；`agent_runner_loop(...)` = `render_events(...)` 包装保兼容；`_wrap_text` / `_wrap_tool` 辅助函数；用延迟 import 解循环依赖 |
| `bd785ec` | **1.2-2a** | `taumain.py` `run()` 改 `for event in events:` 直接迭代事件流 + `event_queue.put(event)`；display_queue 仍传 str dict（双发共存） |
| `99e9817` | **1.2-2b1** | tui `AgentSession` + `ChatMessage` 加 `events` 字段；tui 起 `_consume_event_queue` 线程；删除 tui `_consume_display_queue` |
| `72038ab` | **1.2-2b2** | tui 主 UI 基于事件边界切 turn；删 `_TOOL_USE_RE`、删 `_render_tool_use_block`；`_event_turns` / `_turn_title` 模块级辅助 |
| `160a8a2` | **1.2-2c** | `apps/web/conductor.py` `SubAgentState.events`；新增 `monitor_event_queue`；删 `_TURN_SPLIT_RE` / `_SUMMARY_RE` / `extract_last_summary` / `extract_last_text_reply`；改用 `_last_turn_text(events, running)` |
| `cfd447e` | **1.2-2d-1** | `apps/common/{btw,review,continue}_cmd.py` 全部从 `display_queue.put(text)` 改为 `event_queue.put(RawText(text)) + event_queue.put(TurnEnded({"result":"SYSTEM_MESSAGE"}))` |

测试新增（5 个文件，**全部用 `.venv/bin/python` 跑过**）：
- `tests/test_tau_agent_events.py`（12 cases）— 每事件类型 + 全序列 round-trip
- `tests/test_tau_agent_loop_events_diff.py`（7 scenarios）— golden diff: text+tool / tool-not-yield fence 边界 / no_tool task-done / should_exit / task_mode / non-verbose / yield_info dict interleave
- `tests/test_tau_agent_handler_host.py`（6 cases）— FakeHost + _FakeResponse 覆盖所有 parent 反向依赖点
- `tests/test_tui_event_segments.py`（4 cases）— _event_turns / _turn_title

```
13 files changed, 1028 insertions(+), 127 deletions(-)
```

---

## 三、当前卡在哪

**没有卡。** 用户上一条是「1 继续」——结合我推荐选项 1「停在这 review + smoke」，意思是 review/smoke 后再决定。用户当时没让我开 stage 3 或死代码清理。

**最稳妥的下一步是「等用户跑 smoke」**：
- tui 是改动最大的一处（删了 `_TOOL_USE_RE` regex 解析）。需要用户在真实对话里跑几轮带 tool 的 prompt，看 turn 切分、tool_use 渲染、tool_result 渲染是否和 1.2-1 之前的字节级输出完全等价。
- conductor 子代理是另一个改动点 —— `monitor_event_queue` 取代 `monitor_display_queue`，需要看 web UI 卡片实时更新是不是仍正常。

---

## 四、下一步计划（按用户反馈分支）

### 选项 A：用户跑完 smoke 通过 → 进 **stage 3**

**stage 3 = `apps/common/continue_cmd.py` 的历史回放事件化**。

现状：`continue_cmd.py:339 extract_ui_messages` 把 `model_responses_*.txt` log 逆向工程成同形状字符串，喂给 tui 的 fold_turns。这是 1.2 阶段的最后一处字符串契约残存。

需要做的事：
1. 让 `agent_runner_loop_events` 在写 log 时**同时写一份结构化 event log**（或同步在 `model_responses_*.txt` 旁追加 `.events.jsonl`）
2. `extract_ui_messages` 改为消费 `.events.jsonl`（直接 `for event in events: ...`）
3. 删 `_format_tool_use` / `_format_tool_result` / `_format_response_segment` / `_tool_results_from_prompt` —— 它们存在的全部理由就是逆向工程字符串

### 选项 B：用户跑完 smoke 发现问题 → 修

可能性最大的两个坑（见第六节「踩过的坑」）：
- tool_use 边界：tool_use XML 的 `</tool_use>` 后是否跟紧 tool_result fence，golden diff 已覆盖，但 tui 折叠的真实视觉可能和字符串版略有差
- verbose=False vs verbose=True 渲染差异：`_last_turn_text` 默认 verbose=False，但 tui 显示是 verbose=True —— 如果用户对照 live vs 回放发现不一致，看 `_last_turn_text` 的 `verbose=False` 是否该改

### 选项 C：用户想清死代码

不紧急，但可以做：
- 删 tui `_consume_display_queue`（已无人 put 了 —— common cmd 全转 event_queue）
- 删 `_agent_runner_loop_str_legacy`（golden diff 测已固化其行为，再留着只是冗余）
- 但 `agent_runner_loop(...)` 包装器（events render 适配）暂时保留 —— `taumain.py:184` 还在调用，下一阶段才能拆掉

---

## 五、Tau 硬约束（CLAUDE.md + memory）—— 下个会话别再撞

来自 `CLAUDE.md`：
- **结构勿大重排**：`src/tau_coding`、`src/tau_agent`、`src/tau_ai`、`TMWebDriver/`、`apps/{common,tui,web,im,gui,pet,desktop,hub}` 位置固定
- **包管理用 `uv`**，别用 pip/venv/poetry
- **`memory/` 是白名单**：`.py` 是工具，`.md` 是 SOP；增删条目要**同步**改 `.gitignore` 的 `!memory/...` 解禁项
- **CLAUDE.md ≠ Tau 运行时**：本文件只供开发期 Claude Code 读；Tau 运行时 Agent 读的是 `assets/prompts/sys_prompt.txt` + `memory/`

来自 memory（必须亲自 grep 验证 review subagent 的声称，不能直接采信 —— 这是这次 review 撞过的一个雷）：
- `monorepo-offlimits-core-taumain-refs`：旧启动入口已删除；后续检查应以当前包入口为准

---

## 六、踩过的坑（绝对不要重蹈）

### 6.1 Edit 工具的 `old_string` 必须严格匹配

事件化的几次 Edit 都因字符串不匹配失败。**重写前必读**：
- 用 `print(f'{i}: {repr(line)}')` 看 Python repr（包括不可见字符、空行、`\n` 数量）
- 不要假设「看起来一样」，尤其是跨多行、有空行、有特殊字符的情况
- `old_string` 必须**唯一**地匹配文件，否则 Edit 会失败而不是报错（除非开 `replace_all`）

### 6.2 循环依赖：`events.py` ↔ `agent_loop.py`

`events.py` 需要 `agent_loop.get_pretty_json`（render tool 块要用），`agent_loop.py` 需要 events 类 yield。

**解法**：`agent_loop.py` 用**函数内延迟 import**（不是模块顶部 import）：

```python
def agent_runner_loop_events(...):
    from tau_agent.events import TurnStarted, AssistantTextChunk, ...  # 在函数里
    ...
```

不要用 `TYPE_CHECKING` 假装避开，那是给 mypy 看的，运行时照样炸。

### 6.3 ToolOutputStart / End 必须拆开

最初的 ToolCallStart 设计成**包含 fence-open**（tool_use XML + ```` ``` ````），但 `agent_loop.py:85` 的 `v = next(gen)` 是**门控**的 —— tool 不 yield 时，fence 也不会写。

**结果**：ToolCallStart 会被发出，但 fence-open 永远不见。崩溃时 fence 不闭合。

**修复**：拆成 `ToolCallStart`（header-only，无 fence）+ `ToolOutputStart` / `Chunk` / `End`（fence + body + close）。`render_event` 知道怎么把它们拼回去。

这条坑写进 memory 了（下次写类似多步产出协议时记得先想清楚**条件 yield vs 顺序 yield**）。

### 6.4 stage 2b1 的回归：tui 切 event_queue 后 slash 命令输出消失了

**症状**：用户输 `/btw 进展如何？`，tui 不显示任何回复。

**根因**：common cmd 仍往 `display_queue` 推文本，但 tui 已不消费 `display_queue`。

**修复**：cfd447e（stage 2d-1）—— common cmd 改 `event_queue.put(RawText(...)) + TurnEnded({"result":"SYSTEM_MESSAGE"})`。

**教训**：双发过渡期间，**任何仍在用旧 queue 的 producer 都要同步迁**。不要等 stage 3 统一处理 —— tui 一断开，slash 命令就成了哑巴。

### 6.5 display_queue 没法一刀删

`display_queue` 不只 tui 消费：
- `apps/streamlit_*`（4 个变体，streamlit app family）
- `apps/gui/`
- `apps/im/feishu/`

这些没动。这次只切了 tui/web/common 三个主流前端，**display_queue 必须长期共存**，不能删。

**结论**：`event_queue` 和 `display_queue` 是**长期双轨**，不是过渡期方案。下次有人提「合并两个 queue」时把这个事实摆出来。

### 6.6 golden diff 测试要靠 legacy 函数

stage 1 删旧 `agent_runner_loop` 会让 diff 测试无参照。**保留 `_agent_runner_loop_str_legacy`**（重命名而非删），让 `test_tau_agent_loop_events_diff.py` 拿 `legacy()` 和 `events_render(events)` 逐 yield 比对。

**什么时候能删 legacy**：所有调用方都不再依赖 str yield。短期做不到 —— `taumain.py:184` 还在调包装版的 `agent_runner_loop`。

### 6.7 测试 Python 版本

`.venv/bin/python` 是工作版本。**别用 `uv run pytest`** —— 项目没装某些依赖（fastapi 等）时 `uv run` 会去重装或换 Python 版本，浪费时间。

直接 `.venv/bin/python -m pytest tests/test_xxx.py -v` 跑单个文件即可。

### 6.8 review subagent 会编造声称

具体例子见 memory `review-subagent-fabricates-claims.md`：

- 这次 review 它说「tui 有 `_TURN_SPLIT_RE` 常量」—— **没有**，tui 是内联正则，纠正了
- 这次 review 它说「continue_cmd 是第三遍实时解析」—— **不是**，continue_cmd 是为复用 fold_turns 把历史 log 逆向工程成同形状字符串，纠正了

**铁律**：subagent 给的 file:line 和统计数字，**亲自 grep / Read 验证**后再采信。本会话第一轮 review 已经撞过一次。

### 6.9 `inline_eval ns['parent']` 暗门

`tau_agent/handler.py` 历史上给 inline_eval 暴露了 `parent`（即 Tau 实例），导致任何 do_code_run 能 `parent.llmclient.backend.history = ...` 整个搅乱。

stage 1.3-B（d0f62d7）通过 `Tau.history_snapshot()` 方法 + handler 协议，**显式窄化接口**。任何 inline_eval 想摸 backend，必须走 `host.history_snapshot()` 返回 JSON 字符串。

**教训**：这类暗门只有关闭一种解法，不要试图「缩小权限」—— 它从来不会被缩小。

---

## 七、关键文件位置（接手时直查）

| 路径 | 用途 |
|---|---|
| `src/tau_agent/events.py` | 9 个 dataclass 事件 + `render_event(event, verbose)` |
| `src/tau_agent/agent_loop.py` | `_agent_runner_loop_str_legacy`（golden ref）+ `agent_runner_loop_events` + `agent_runner_loop`（包装） |
| `src/tau_agent/handler.py` | `HostContext` Protocol + `TauHandler` |
| `src/tau_coding/taumain.py` | `Tau` 类 + `run()` 消费事件流 |
| `apps/tui/app.py` | `_event_turns` / `_turn_title` / `_consume_event_queue` |
| `apps/web/conductor.py` | `_last_turn_text(events, running)` / `monitor_event_queue` |
| `apps/common/{btw,review,continue}_cmd.py` | 改用 event_queue put RawText + TurnEnded |
| `tests/test_*` 5 个新测试 | 上面表里列了 |

---

## 八、memory 待更新（不紧急，但要做）

`memory/typed-event-refactor-plan.md` 现在说「**待拍板**」三个取舍点（流式粒度 / display_queue 半径 / 历史回放），9 个 commit 下来都拍板了：

- 流式粒度 → AssistantTextChunk 已保留（不只发完成态）
- display_queue 半径 → **长期共存**，不能合并
- 历史回放 → 已成 stage 3 单独项

更新时一并把「已完成的 9 个 commit」列进去，下次会话不必重新挖 git log。

---

## 九、TL;DR

**状态**：9 commit 已落地，golden diff 通过，前端三处（tui/web/common）已切到 event_queue。**等用户跑 smoke 反馈。**

**优先做的**：
1. 用户跑 smoke
2. 没炸 → stage 3（continue_cmd 历史回放事件化）
3. 炸了 → 看是 golden diff 漏了哪个 case 还是 verbose 切换问题

**绝对不要**：
- 删 `display_queue`（streamlit/gui/im 还在用）
- 删 `_agent_runner_loop_str_legacy`（taumain 还在间接依赖）
- 改目录结构（CLAUDE.md 硬约束）
- 信 review subagent 的具体数字（亲自 grep）
