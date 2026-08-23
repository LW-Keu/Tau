"""唯一仓库根锚点。所有'仓库根相对'路径解析的单一来源。
TAU_HOME 可被环境变量覆盖（scheduled task / 容器 / CI 友好）；
否则回溯到本文件上两级（src/ 的父目录 = 仓库根）。
作为 stdlib-only 叶子模块，被 tau_ai/tau_agent/tau_coding/apps 共享。"""
import os
from pathlib import Path

TAU_HOME = Path(os.environ.get("TAU_HOME")
                or Path(__file__).resolve().parents[2])
ASSETS = TAU_HOME / "assets"
MEMORY = TAU_HOME / "memory"
TEMP = TAU_HOME / "temp"
SCHE_TASKS = TAU_HOME / "sche_tasks"
TAU = TAU_HOME / ".tau"
TAUKEY_PATH = TAU / "taukey.py"


def require_assets() -> None:
    """clone-to-run 守护：assets/ 缺失（如 pip 安装、无 checkout）时尽早
    给出可操作错误，而不是等读 sys_prompt 时才崩。"""
    if not (ASSETS / "prompts").is_dir():
        raise SystemExit(
            f"[tau] 未找到运行时资源目录: {ASSETS}\n"
            "Tau 采用 clone-to-run 模型：pip 安装的 tau 不能独立运行。\n"
            "请 git clone 仓库后在仓库内运行，或设 TAU_HOME 指向一份完整 checkout。"
        )
