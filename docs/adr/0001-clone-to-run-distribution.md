# Clone-to-run：wheel 不是运行时分发渠道

Tau 运行时除了 import 包代码，还按 checkout 布局读 `assets/`（sys_prompt、tools_schema、模板、注入头、providers 表），并依赖 `memory/`、`sche_tasks/`、`temp/` 等仓库目录。因此分发模型定为 **clone-to-run**：用户 `git clone` + editable install（`uv pip install -e .`），`tau_coding.paths.TAU_HOME` 锚定仓库根（可用环境变量覆盖）。

`pyproject.toml` 产出的 wheel（含 `tau` entry point）仅用于开发期验证 import 边界（见 `scripts/smoke_packaging.py`）：wheel 显式排除 `assets*`，pip 装进 site-packages 后 `parents[2]` 锚点失效，agent 无法启动。`tau_coding.paths.require_assets()` 在 CLI 启动时给出可操作报错，替代深栈 traceback。

## Considered Options

让 wheel 自包含（资产入包 + `importlib.resources` 读取）——否决：`memory/` SOP、`sche_tasks/`、`temp/` 仍依赖整个 checkout，自包含 wheel 只是"半自包含"的假象，收益不抵改动。若将来这些运行时状态全部从 checkout 剥离，可重开此决策。
