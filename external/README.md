# external/

外部组件（定义见 `CONTEXT.md`）：自成一体、与 Tau 核心保持一臂距离、可独立演进的组件。

| 条目 | 这是什么 | 形态 | 谁调它 |
|---|---|---|---|
| `agent_bbs.py` | 独立 FastAPI 公告板应用（`python agent_bbs.py`） | 独立进程，不进 wheel | `memories/goal_hive_sop.md`；用户手动启停 |
| `TMWebDriver/` | 浏览器自动化驱动（保留登录态）+ Site Skills + 多平台发布 | 库，随 wheel 分发 | `tau_agent.tools.web`、`memories/daily_report_fetch.py` |
