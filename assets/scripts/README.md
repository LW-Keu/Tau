# assets/scripts/

代码形态的资产（定义见 `CONTEXT.md`）：运行时被**读成文本**注入，而非被 import 的模块。

| 文件 | 这是什么 | 谁调它 |
|---|---|---|
| `code_run_header.py` | `code_run` 工具的 subprocess 注入头 | `src/tau_agent/tools/code_run.py` |

设置向导（configure_* / install-*）已迁至顶层 `setup/`。
