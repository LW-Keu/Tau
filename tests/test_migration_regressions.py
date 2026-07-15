import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_active_files_have_no_legacy_slash_launch_paths():
    roots = [ROOT / name for name in ("AGENTS.md", "README.md", "assets", "memory", "scripts", "src", "apps")]
    suffixes = {".md", ".py", ".sh", ".cmd", ".toml", ".json", ".yaml", ".yml"}
    patterns = (
        r"(?:^|[\s`'\"(])(?:\.\./)*core/taumain\.py",
        r"(?:^|[\s`'\"(])(?:\.\./)*tau_cli/",
        r"(?:^|[\s`'\"(])(?:\.\./)*reflect/",
        r"(?m)^\s*(?:from|import)\s+(?:core|tau_cli|reflect)(?:\.|\s|$)",
    )
    offenders = []
    for root in roots:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if path.is_file() and path.suffix in suffixes:
                text = path.read_text(encoding="utf-8", errors="replace")
                if any(re.search(pattern, text) for pattern in patterns):
                    offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_streamlit_entrypoint_local_imports_resolve_without_execution():
    app = ROOT / "apps" / "web" / "streamlit" / "app_v4.py"
    tree = ast.parse(app.read_text(encoding="utf-8"))
    local_names = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module
        and (app.parent / f"{node.module.split('.')[0]}.py").exists()
    }
    declared_local = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module == "upload_utils"
    }
    assert declared_local == {"upload_utils"}
    assert local_names == declared_local
    sys.path.insert(0, str(app.parent))
    try:
        assert all(importlib.util.find_spec(name) for name in local_names)
    finally:
        sys.path.pop(0)


def test_taumain_import_has_no_resource_warning():
    result = subprocess.run(
        [sys.executable, "-W", "always::ResourceWarning", "-c", "import tau_coding.taumain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ResourceWarning" not in result.stderr
