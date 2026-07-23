import locale
import os
import random
import sys

from tau_paths import ASSETS, MEMORY, TAU_HOME


def language_suffix():
    return "_en" if os.environ.get("GA_LANG") == "en" else ""


def initialize_runtime():
    lang = locale.getlocale()[0] or ""
    os.environ.setdefault(
        "GA_LANG",
        "zh" if any(key in lang.lower() for key in ("zh", "chinese")) else "en",
    )
    _configure_stdio()
    MEMORY.mkdir(parents=True, exist_ok=True)
    _create(MEMORY / "global_mem.txt", "# [Global Memory - L2]\n")
    template = ASSETS / f"template/global_mem_insight_template{language_suffix()}.txt"
    _create(
        MEMORY / "global_mem_insight.txt",
        template.read_text(encoding="utf-8") if template.exists() else "",
    )
    _initialize_cdp_config()
    from tau_agent.plugins.hooks import discover_and_load
    discover_and_load()


def _configure_stdio():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    elif hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    elif hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")


def _create(path, content):
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _initialize_cdp_config():
    path = TAU_HOME / "external/TMWebDriver/tmwd_cdp_bridge/config.js"
    if path.exists():
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        token = hex(random.randint(0, 99999999))[2:8]
        path.write_text(f"const TID = '__ljq_{token}';", encoding="utf-8")
    except OSError as exc:
        print(f"[WARN] CDP config init failed: {exc} — advanced web features unavailable.")
