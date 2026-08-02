# Tau 接入 WorkBuddy 配置指南

> 把 Tau 跑成本地 OpenAI 兼容服务，让 WorkBuddy 通过「自定义模型」调用 Tau 的完整本地工具集。
>
> 首版仅支持本机、单用户、纯文本输入；WorkBuddy 的不同对话相互隔离。

---

## 📋 目录

1. [前置条件](#前置条件)
2. [安装 API 依赖](#安装-api-依赖)
3. [配置 LLM 后端](#配置-llm-后端)
4. [设置 API 密钥](#设置-api-密钥)
5. [启动服务](#启动服务)
6. [在 WorkBuddy 中配置自定义模型](#在-workbuddy-中配置自定义模型)
7. [验证 & 排错](#验证--排错)
8. [常见问题](#常见问题)

---

## 前置条件

| 项目 | 要求 |
|---|---|
| Python | 3.10 – 3.13 |
| Tau 项目 | 本仓库已 `git clone` 并可运行 `tau configure` 通过 |
| LLM 凭证 | 至少一个可用的 LLM API Key（已写入 `.tau/taukey.py`） |
| 网络 | 仅本机回环，**不需要外网**（Tau 调 LLM 时才需要） |
| WorkBuddy | 桌面客户端，且支持自定义 OpenAI 兼容端点 |

> 端口默认 `8642`，如被占用可在启动时加 `--port N` 改。

---

## 安装 API 依赖

API 前端用的是 `fastapi` + `uvicorn`，属于可选依赖，**不会随 `uv sync` 自动安装**，需要单独装：

```bash
uv pip install -e ".[api]"
```

> 如果你还想装 GUI/Web/TUI，请用 `.[ui]`；一键装全应用请用 `.[all-apps]`。

---

## 配置 LLM 后端

服务跑起来后，Tau 真正干活还得靠一个 LLM 后端。**没有 `.tau/taukey.py` 跑不起来：**

首次使用：
```bash
tau configure      # 向导式生成 .tau/taukey.py
```

已有 `taukey.py`，手工编辑也 OK，示例（OpenAI 兼容协议）：
```python
my_model = {
    'type': 'native_oai',           # OpenAI 兼容 + 原生工具调用
    'apikey': 'sk-你的密钥',
    'apibase': 'http://你的API地址:端口',
    'model': '模型名称',
}
```

| `type` | 适用 |
|---|---|
| `native_oai` | GPT / Kimi / DeepSeek / GLM / Qwen / MiniMax 等 |
| `native_claude` | Claude API |
| `oai` / `claude` | 旧文本协议，工具调用走文本 |

> 注意：`type` 必须是 `native_*` 才能解锁 Tau 的原生工具调用；纯文本 `oai/claude` 会限制工具能力。

---

## 设置 API 密钥

API 服务用 **Bearer Token** 鉴权，必须通过环境变量 `TAU_API_KEY` 提供，**不传直接拒启**：

```bash
# 任意强随机字符串都行，例如:
export TAU_API_KEY='wb-local-9f3c2e1a-2026'
```

临时一次性也行：
```bash
TAU_API_KEY='wb-local-9f3c2e1a-2026' tau api
```

> 这把密钥同时也是你在 WorkBuddy 客户端填写的「API Key」。**别用你 LLM 的真 Key** —— WorkBuddy 只需要它来验 Tau 的 HTTP 请求。

---

## 启动服务

最简：
```bash
TAU_API_KEY='wb-local-9f3c2e1a-2026' tau api
```

换端口：
```bash
TAU_API_KEY='...' tau api --port 9000
```

跑起来后日志会显示：
```text
Uvicorn running on http://127.0.0.1:8642
```

提供三个端点：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查，无需鉴权 |
| GET | `/v1/models` | 列出模型（返回 `tau-agent`），需 Bearer |
| POST | `/v1/chat/completions` | OpenAI 兼容对话，支持 `stream=true` SSE |

---

## 在 WorkBuddy 中配置自定义模型

进入 WorkBuddy → **设置 → 自定义模型 / Custom Model**，新增一项：

| 字段 | 值 |
|---|---|
| API URL | `http://127.0.0.1:8642/v1` |
| API Key | 与 `TAU_API_KEY` 完全一致 |
| Model | `tau-agent` |

> - 端口不填默认 `8642`；改了 `--port` 这里也要跟着改。
> - **不要**填 WorkBuddy 公网地址 —— 服务只绑 `127.0.0.1`，外网根本访问不到。

保存后即可在 WorkBuddy 里选 `tau-agent` 与 Agent 对话。Tau 的内部工具（浏览器 / OCR / 桌面 / 文件等）会被自动调用，**WorkBuddy 只会看到普通的文本流**。

---

## 验证 & 排错

**1. 端口探活**
```bash
curl http://127.0.0.1:8642/health
# → {"status":"ok"}
```

**2. 模型发现**
```bash
curl -H "Authorization: Bearer $TAU_API_KEY" http://127.0.0.1:8642/v1/models
# → {"object":"list","data":[{"id":"tau-agent",...}]}
```

**3. 非流式对话**
```bash
curl -X POST http://127.0.0.1:8642/v1/chat/completions \
  -H "Authorization: Bearer $TAU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tau-agent",
    "messages": [{"role":"user","content":"用一句话介绍你自己"}],
    "stream": false
  }'
```

**4. 流式对话（SSE）**
```bash
curl -N -X POST http://127.0.0.1:8642/v1/chat/completions \
  -H "Authorization: Bearer $TAU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tau-agent",
    "messages": [{"role":"user","content":"帮我在桌面写 hello.txt,内容 Hello World"}],
    "stream": true
  }'
```

> 观察到 `data: {...}` 一行行流出，且包含工具调用过程的中间文本，即为正常。

---

## 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 启动报 `TAU_API_KEY is required` | 没 `export` 或没在 `tau api` 前加环境变量 |
| 启动报 `ModuleNotFoundError: fastapi` | 没装 `.[api]`，重跑 `uv pip install -e ".[api]"` |
| `401 invalid_api_key` | WorkBuddy 填的 API Key 与 `TAU_API_KEY` 不一致（含多余空格/换行） |
| `400 model_not_found` | model 字段不是 `tau-agent`（区分大小写） |
| WorkBuddy 找不到模型 | 先确认 `tau api` 在跑、`curl /v1/models` 能回列表 |
| 连接被拒 | 服务只绑 `127.0.0.1`，**WorkBuddy 必须装在同一台机器** |
| 端口占用 | 启动时 `tau api --port 9000`，WorkBuddy 的 API URL 也要改 |
| 对话没工具能力 | `.tau/taukey.py` 用了非 `native_*` 的 `type`，改成 `native_oai` / `native_claude` |
| 长任务卡住 | Tau 在调工具，是正常等待；WorkBuddy 关掉当前对话 → 服务只 abort 这个请求 |

---

## 设计说明（选读）

- 每个 `/v1/chat/completions` 请求**独立创建**一个 `Tau` 实例、独立的工具调用历史、独立的 abort 信号；WorkBuddy 关闭一个对话不会影响另一个。
- WorkBuddy 发来的历史消息会被拼成一段带角色标签的上下文，最后一条 user 消息作为本轮请求。**Tau 内置系统提示依然权威**，WorkBuddy 的 system 消息仅作附加指令。
- 服务**无状态**：不保存跨请求的会话记录，重启即清空。每次请求历史都靠 WorkBuddy 重发。
- 首版不支持：图片/附件、多模态、远端多用户、OpenAI Responses API、Tools/Function Calling 结构化输出。

更多设计取舍见 `docs/superpowers/specs/2026-08-02-workbuddy-api-server-design.md`。