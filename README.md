<div align="center">

# Tau

**极简、自进化的自主智能体框架**

*Minimalist · self-evolving · autonomous agent framework*

![Python](https://img.shields.io/badge/Python-3.10%E2%80%933.13-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/status-early%20%26%20active-orange)
![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

[快速开始](#-快速开始) · [能力一览](#-能力一览) · [架构](#-架构) · [项目现状](#-项目现状与演进) · [文档](#-进一步阅读)

</div>

---

Tau 是一个**极简内核 + 越用越强**的自主智能体框架。运行时代码位于 `src/tau_coding`、`src/tau_agent` 和 `src/tau_ai`,运行时资产位于 `assets/` 和 `memory/`,能驱动一个会读自己源码、自己装依赖、把每次成功经验固化成技能的 Agent。

它不预设一长串功能,而是给你一个能**自我进化**的最小系统:跑起来之后,你只需用一句话告诉它要什么,它会自己读代码、找依赖、解锁能力,并把执行路径沉淀成可复用的 Skill——使用越久,它越懂你。

## ✨ 核心理念

| | 理念 | 说明 |
|---|---|---|
| 🪶 | **极简内核** | 核心运行时收敛在 `src/tau_*` 包。更多功能应让代码*收缩*而非膨胀——好的抽象,新功能只增加实现,不修改旧逻辑。 |
| 🧬 | **越用越强** | 不预置技能。每完成一个新任务,自动将执行路径固化为 Skill,逐渐长成一棵专属于你的技能树。 |
| 📖 | **代码即文档** | Agent 能读懂自己的源码。任何模式怎么用,不必查手册——直接问它「看你的代码,告诉我 X 怎么启用」。 |
| 🌱 | **环境自举** | 先把最小系统跑起来,需要什么工具再让 Agent 自己安装,而不是预先装一堆重依赖。 |

## 🚀 快速开始

> 完整图文引导见 [GETTING_STARTED.md](docs/GETTING_STARTED.md);平台差异、Key 配置与排障见 [installation_zh.md](docs/installation_zh.md)。

### 1. 安装

**一键安装(推荐普通用户)** — 自动准备隔离环境、下载 Tau、装好核心依赖:

```bash
# macOS / Linux
curl -fsSL http://fudankw.cn:9000/files/ga_install.sh | bash
```

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -c "irm http://fudankw.cn:9000/files/ga_install.ps1 | iex"
```

**开发者安装(可编辑源码)** — 推荐 Python **3.11 / 3.12**(⚠️ 不支持 3.14),包管理用 [uv](https://github.com/astral-sh/uv):

```bash
git clone https://github.com/lllIlIlIlll/tau.git
cd tau
uv venv
uv pip install -e ".[ui]"            # 核心 + UI 依赖
mkdir -p .tau
cp assets/template/taukey_template.py .tau/taukey.py  # 填入你的 LLM API Key
# 填好 .tau/taukey.py 后:
uv run tau launch
```

> `.[ui]` 会一次性安装以下 UI 后端；只需要 API 服务时可安装 `.[api]`,想一次装全应用依赖可安装 `.[all-apps]`:
> - streamlit   (Web,  apps/web/streamlit/)
> - pywebview   (Hub/Launch 桌面壳, apps/hub/)
> - textual     (TUI,  apps/tui/app.py)
> - aiohttp     (Pet,  apps/pet/bridge.py)
> - PySide6     (GUI,  apps/gui/app.py)

### 2. 配置模型

编辑 `.tau/taukey.py`，用 `type` 明确指定接口格式：

```python
my_model = {
    'type': 'native_oai',
    'apikey': 'sk-你的密钥',
    'apibase': 'http://你的API地址:端口',
    'model': '模型名称',
}
```

| `type` | 接口格式 | 适用 |
|---|---|---|
| `native_oai` | OpenAI 兼容 + 原生工具调用 | 多数 API 服务、GPT、Kimi、DeepSeek、GLM、Qwen、MiniMax… |
| `native_claude` | Anthropic 兼容 + 原生工具调用 | Claude API 服务 |
| `oai` / `claude` | 文本协议工具调用 | 旧渠道兼容 |

> 不想手填?运行向导:`tau configure`(即 `setup/configure_taukey.py`)。

### 3. 启动

通过 `tau` 命令选择前端；开发环境未激活时可写成 `uv run tau ...`:

```bash
tau cli        # CLI 对话,最轻量(tau_coding.taumain)
tau tui        # 终端图形界面(Textual),适合 SSH / 纯终端
tau gui        # 桌面聊天界面(PySide6)
tau launch     # 原生窗口壳(pywebview)
tau hub        # Hub 管理面板(系统托盘 + 浏览器)
tau api        # WorkBuddy 兼容 API(仅监听本机)
tau configure  # 初始配置向导,生成/更新 .tau/taukey.py
tau run "帮我总结当前项目"  # 同步运行单次任务,适合脚本化调用
tau status     # 检查 Tau 进程状态
tau update     # git pull + uv sync 更新项目
tau list       # 列出全部命令
```

第一个任务可以试试:`帮我在桌面创建一个 hello.txt,内容是 Hello World`。

## 🧠 能力一览

环境跑起来后,大多数能力**只需对 Agent 说一句话**即可解锁——它会自己读代码、装依赖、配置好:

| 领域 | 能力 |
|---|---|
| 🌐 **浏览器自动化** | 在保留登录态的真实浏览器中操作(`TMWebDriver`);Site Skills、多平台一键发布 |
| 🖱️ **桌面 / 视觉** | 屏幕 OCR、Vision 看屏、UI 元素检测 |
| 📱 **移动端** | 通过 ADB 控制 Android 设备 |
| 💬 **聊天平台接入** | 微信 / QQ / 飞书 / 企业微信 / 钉钉 / Telegram —— 随时用手机给 Agent 发指令 |
| 📰 **日常自动化** | 每日报告(分层多源采集)、邮件发送、计划任务调度 |
| 🧩 **高级模式** | Reflect 反射 · Plan 规划 · SubAgent 子代理 · Goal 目标模式 · 自主探索 |

## 🖥️ 多前端

同一个内核,多种使用形态,按场景挑一个即可:

| 前端 | 启动 | 形态 |
|---|---|---|
| CLI | `tau cli` | 命令行对话,最轻量 |
| TUI | `tau tui` | Textual 终端界面,多会话 + 流式 |
| GUI | `tau gui` | PySide6 桌面聊天(气泡高亮、拖拽、历史搜索) |
| Web | `tau launch` / `apps/web/` | Streamlit + pywebview 桌面壳 |
| Hub | `tau hub` | 托盘 + 浏览器管理面板 |
| API | `tau api` | WorkBuddy 兼容的本机 OpenAI API |
| Pet | `apps/pet/` | 桌面宠物悬浮窗 |
| Desktop | `apps/desktop/` | Tauri 原生客户端 |
| IM | `apps/im/` | 即时通讯 Bot 接入 |

### WorkBuddy 接入

安装 API 依赖，在 `.tau/.env` 中设置一个仅供本机使用的密钥，然后启动服务：

```bash
uv pip install -e ".[api]"
mkdir -p .tau
printf 'TAU_API_KEY=请替换为本机密钥\n' > .tau/.env
tau api
```

在 WorkBuddy 的「自定义模型 / Custom Model」中填写：

- API URL：`http://127.0.0.1:8642/v1`
- API Key：与 `.tau/.env` 中的 `TAU_API_KEY` 相同
- Model：`tau-agent`

首版仅支持本机、纯文本输入。WorkBuddy 的不同对话相互隔离；历史由
WorkBuddy 随请求提供，Tau 的内部工具调用记录不跨请求保存。

## 🧱 架构

```
Tau/
├── src/          # 可安装包:tau_coding(入口 · CLI · reflect) · tau_agent · tau_ai
├── apps/         # 多前端/通道:common · api · tui · gui · web · pet · desktop · im · hub
├── memory/       # 技能库:.py 是工具(Agent import 调用),.md 是 SOP(Agent 阅读执行)
├── external/     # 外部组件:TMWebDriver(浏览器自动化,保留登录态) · agent_bbs
├── setup/        # 设置向导,如 tau configure 调用的 taukey 配置器
├── examples/     # 示例配置、任务定义与接入样品
├── tests/        # 自动化测试与开发期烟测
├── sche_tasks/   # 计划任务
├── docs/         # 文档
└── assets/       # 系统提示词 · 工具 schema · 模板 · 脚本
```

**技能 = 记忆**:`memory/` 是 Tau 的成长所在。`.py` 文件是可被 Agent `import` 的工具,`.md` 文件是供 Agent 阅读执行的 SOP。Agent 在使用中不断向这里写入新技能。

## 🤖 模型支持

原生支持两类协议,在 `.tau/taukey.py` 中用 `type` 字段显式配置,可多模型并存:

- **OpenAI 兼容接口** — GPT 系列、Kimi、DeepSeek、GLM、Qwen、MiniMax,以及经 OAI 兼容网关接入的 Gemini 等
- **Anthropic Claude 原生接口** — Claude Messages API
- **Mixin 故障转移** — 多个 native session 可按优先级轮换,适合把主力模型和备用渠道组合起来

启动时按系统语言自动切换中 / 英（可用 `TAU_LANG` 覆盖）。

## 📅 项目现状与演进

> Tau 仍处于**早期高速迭代**阶段。当前开发主线为 `tau-v5.0.0`,`tau --version` 报告内核版本 `v0.1.0`。功能、前端和内部事件协议仍在演进,接口可能变动。

| 时间 | 里程碑 |
|---|---|
| 2026-06-15 | 🎉 项目诞生(initial commit),极简内核成型 |
| 2026-06-20 | 每日报告(daily report)分层多源采集系统上线 |
| 2026-06-21 | 邮件子系统 **v2.1** —— 配置 / 发送规格化 |
| 2026-06-22 | 建立唯一仓库根锚点(现为 `src/tau_coding/paths.py`) |
| 2026-06-26 | TMWebDriver **Site Skills** 系统;`apps/` 前端包脚手架 |
| 2026-06-27 | 前端统一收敛到 `apps/`(数据驱动 launcher);邮件 **v2.2** 多发件人 |

## 📚 进一步阅读

- 🚀 [新手上手指南 GETTING_STARTED.md](docs/GETTING_STARTED.md)
- 🛠️ [安装指南(中文)installation_zh.md](docs/installation_zh.md) · [English](docs/installation.md)
- 🤝 [贡献指南 CONTRIBUTING.md](CONTRIBUTING.md)
- 📘 Datawhale 教程:<https://datawhalechina.github.io/hello-tau/>
- 📄 技术报告:<https://arxiv.org/abs/2604.17091>

## 🤝 贡献

Tau 的核心足够小,**一次坐下就能读完**。动手前请先读懂代码与设计哲学,非小改动请先开 Issue 讨论。

所有 PR 都会经过一套**刻意严格**的自动化代码审查(大多数 AI 生成的代码无法原样通过):自文档化、改动半径小、*更多功能 → 更少代码*、按失败半径让程序崩溃。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 License

[MIT](LICENSE)
