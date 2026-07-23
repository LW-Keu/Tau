"""tau update — git pull + uv sync."""
import os, shutil, subprocess
from ._common import PROJECT_DIR
COMMAND = {
    "name": "update",
    "help": "更新项目 (git pull + uv install)",
    "desc": "从 Git 拉取最新代码并更新依赖",
    "cmd": None,
    "internal": True,
}


def run(args=None):
    if not shutil.which("uv"):
        raise RuntimeError("tau update 需要 uv，请先安装 uv")
    os.chdir(PROJECT_DIR)
    print("🔄 git pull...")
    r = subprocess.run(["git", "pull"], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
    print("📦 uv sync...")
    install_cmd = ["uv", "sync"]
    r2 = subprocess.run(install_cmd, capture_output=True, text=True)
    print(r2.stdout[-500:] if r2.stdout else "")
    if r2.returncode != 0:
        print(r2.stderr[-500:])
