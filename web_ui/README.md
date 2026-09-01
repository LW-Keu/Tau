# web_ui — Tau 聊天前端

TypeScript + React + Vite,对接 `apps/api/server.py` 的 OpenAI 兼容接口
(`POST /v1/chat/completions`,SSE 流式)。会话存 localStorage,后端无状态
(每次请求携带完整历史)。

## 运行

```bash
# 1. 启动后端(需要 TAU_API_KEY,默认 127.0.0.1:8642)
uv run python apps/api/server.py

# 2. 启动前端
cd web_ui
npm install
npm run dev        # http://localhost:5173,/v1 由 vite 代理到后端
```

首次打开在左下角「设置」填入 `TAU_API_KEY`。

## 其他命令

```bash
npm test           # SSE 解析单测(vitest)
npm run build      # tsc 检查 + 产出 dist/
```

## 说明

- 后端无 CORS 头。开发用 vite 代理(见 `vite.config.ts`,端口不对改
  `API_ORIGIN`);生产需把 `dist/` 与 API 同源托管。
- Base URL 留空 = 同源(经代理);填了则直连,需后端自行加 CORS。
