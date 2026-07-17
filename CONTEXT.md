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
_Avoid_: 样板、样例片段

**外部组件 (External Component)**:
自成一体、与 Tau 核心保持一臂距离、可独立演进的组件,集中存放于 `external/`。两种合法形态:独立进程(如 `agent_bbs`,手动启停)、被核心 import 的库(如 `TMWebDriver`,随 wheel 分发)。
_Avoid_: 外部资产、插件、伴随服务
