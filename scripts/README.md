# scripts/

开发期烟测集。**不在 wheel**（pyproject `exclude` 显式排除）。**不在用户运行路径**。
Agent 不可见；agent 在 SOP/工具中**只**通过 `tau_agent.tools.*` API 调用业务逻辑。

| 文件 | 这是什么 | 谁调它 |
|---|---|---|
| `smoke_*.py` (×5) | clean-subprocess 烟测，验证 import/wheel 边界 | 开发者手动 |

相关目录：
- 单元测试 → `tests/`
- macOS agent 自动化工具（asrun / as_probe / snapread 等）→ `memory/`（见 `memory/l3_capability_inventory.md` §8.10）
- 第三方 `tau_ai.transport` 接入示例 → `examples/`
