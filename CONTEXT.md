# Tau

极简自进化自主 Agent 框架。本文件是全项目统一语言(ubiquitous language)的唯一来源:术语以此为准,冲突时改代码或改此表,二者必居其一。

## Language

**资产 (Asset)**:
Tau Agent 进程运行期间按需读取的只读文件,集中存放于 `assets/`。判据:agent 跑起来后会不会读它——会则是资产,不会则不是(不论文件类型)。
_Avoid_: 资源、素材、静态文件

**设置向导 (Setup Wizard)**:
用户在首次安装或维护配置时手动运行的交互式工具,集中存放于 `setup/`。Agent 运行时不读;`tau` CLI 可通过子命令代为拉起。
_Avoid_: 配置脚本、安装脚本

**示例 (Example)**:
供用户拷贝或模仿的样品(配置底版、任务定义、输出样例、接入 demo),集中存放于 `examples/`。运行时不读;拷出改字后才生效。
例外:taukey 配置底版存放于 `assets/template/`(`setup/configure_taukey.py` 以其为骨架生成 `.tau/taukey.py`)。
_Avoid_: 样板、样例片段

**外部组件 (External Component)**:
自成一体、与 Tau 核心保持一臂距离、可独立演进的组件,集中存放于 `external/`。两种合法形态:独立进程(如 `agent_bbs`,手动启停)、被核心 import 的库(如 `TMWebDriver`,随 wheel 分发)。
_Avoid_: 外部资产、插件、伴随服务

## 前端与通道

**前端 (Frontend)**:
`apps/` 下面向用户的界面或渠道进程(tui/gui/desktop/web/im/pet/hub)。全部是活的产品表面,不以前端数量收敛为维护手段(ADR-0001)。除 Tauri desktop 经 bridge subprocess 外,均进程内 import `Tau` 并 `put_task` 驱动代理。
_Avoid_: 客户端、界面层

**display_queue / 字符串契约 (String Contract)**:
`taumain` 产出的渲染字符串流,IM 渠道与 streamlit/gui 的**永久**消费契约,非过渡产物。字符串形状即契约,由 golden diff 测试冻结(ADR-0002)。
_Avoid_: 遗留队列、过渡格式

**event_queue / typed event**:
`src/tau_agent/events.py` 定义的结构化事件流(9 类),服务需要细粒度流式交互的前端(tui、conductor 子代理)。与 display_queue 长期双轨并存,不是替代关系(ADR-0002)。
_Avoid_: 新队列、统一事件总线

## 对话

**对话 (Conversation)**:
后端无关的连续交互单元——对话属于用户,模型/后端只是可替换的执行器。切换模型(`/llm`)或恢复会话(`/continue`)时:同协议族无损转移,跨族或非 native 格式走降级。
_Avoid_: 会话(歧义,易与 LLM session 混淆)、聊天

**降级 (Degrade)**:
将无法无损转移的对话历史压缩为摘要后继续的一等操作,非错误路径。触发点:跨协议族切换模型、恢复非 native 格式的历史日志。
_Avoid_: fallback、容错
