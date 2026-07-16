import ast
import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_PREFIXES = (
    "docs/superpowers/plans/",
    "docs/superpowers/specs/",
)
HISTORICAL_FILES = {"docs/SETUP_EMAIL.md"}
NEGATIVE_TEST_SOURCES = {
    "tests/test_migration_regressions.py",
    "tests/test_tau_agent_package.py",
    "tests/test_tau_agent_plugins.py",
    "tests/test_tau_ai_package.py",
    "tests/test_tau_coding_package.py",
}
LEGACY_PATTERNS = (
    re.compile(r"(?<![\w])(?:\.\.?/)*(?:core|tau_cli)/"),
    re.compile(r"(?<![\w])(?<!tau_coding/)(?<!tau_agent/)(?:\.\.?/)*(?:reflect|plugins)/"),
    re.compile(r"(?m)^\s*(?:from|import)\s+(?:core|tau_cli|reflect|plugins)(?:[.\s]|$)"),
    re.compile(r"(?P<q>['\"])(?:core|tau_cli|reflect|plugins)(?:\.[A-Za-z_]\w*)+(?::[A-Za-z_]\w*)?(?P=q)"),
    re.compile(r"/\s*(?P<q>['\"])(?:core|tau_cli|reflect|plugins)(?P=q)"),
    re.compile(r"(?:find_spec|import_module|__import__)\(\s*['\"](?:core|tau_cli|reflect|plugins)['\"]"),
    re.compile(r"sys\.modules\[\s*['\"](?:core|tau_cli|reflect|plugins)['\"]\s*\]"),
)


def _tracked_text_files():
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    for raw_path in listed.split(b"\0"):
        if not raw_path:
            continue
        relative = raw_path.decode()
        if (relative in HISTORICAL_FILES or relative in NEGATIVE_TEST_SOURCES
                or relative.startswith(HISTORICAL_PREFIXES)):
            continue
        path = ROOT / relative
        data = path.read_bytes()
        if b"\0" not in data[:8192]:
            yield relative, data.decode("utf-8", errors="replace")


def _legacy_hits(text):
    normalized = text.replace("\\", "/")
    return [pattern.pattern for pattern in LEGACY_PATTERNS if pattern.search(normalized)]


class MigrationRegressionTests(unittest.TestCase):
    def test_active_tracked_text_has_no_legacy_boundaries(self):
        offenders = [relative for relative, text in _tracked_text_files()
                     if _legacy_hits(text)]
        self.assertEqual(offenders, [])

    def test_legacy_scan_covers_path_module_and_string_forms(self):
        legacy = (
            "core/handler.py",
            "./core/handler.py",
            "/opt/tau/core/handler.py",
            "../tau_cli/config.py",
            "reflect/scheduler.py",
            "plugins/hooks.py",
            r"core\handler.py",
            r"tau_cli\config.py",
            r"reflect\scheduler.py",
            r"plugins\hooks.py",
            "from core.llm import transport",
            "import tau_cli.cli",
            "'reflect.goal_mode'",
            '"plugins.hooks"',
            'root / "core" / "taumain.py"',
            'find_spec("plugins")',
            'tau = "tau_cli.cli:main"',
            '__import__("reflect")',
            'sys.modules["plugins"]',
        )
        current = (
            "src/tau_coding/reflect/scheduler.py",
            "src/tau_agent/plugins/hooks.py",
            r"src\tau_coding\reflect\scheduler.py",
            r"src\tau_agent\plugins\hooks.py",
            "from tau_coding.reflect import scheduler",
            '"tau_agent.plugins.hooks"',
        )
        self.assertTrue(all(_legacy_hits(text) for text in legacy))
        self.assertTrue(all(not _legacy_hits(text) for text in current))

    def test_streamlit_entrypoint_local_imports_resolve_without_execution(self):
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
        self.assertEqual(declared_local, {"upload_utils"})
        self.assertEqual(local_names, declared_local)
        sys.path.insert(0, str(app.parent))
        try:
            self.assertTrue(all(importlib.util.find_spec(name) for name in local_names))
        finally:
            sys.path.pop(0)

    def test_rust_root_discovery_uses_current_package_anchors(self):
        source = (ROOT / "apps" / "desktop" / "src-tauri" / "src" / "lib.rs").read_text()
        discovery = source[source.index("fn find_project_dir_from"):]
        discovery = discovery[:discovery.index("\n}\n")]
        self.assertIn('join("pyproject.toml")', discovery)
        self.assertIn('join("src").join("tau_coding").join("taumain.py")', discovery)
        self.assertNotIn('join("core")', discovery)

    def test_taumain_import_has_no_resource_warning(self):
        result = subprocess.run(
            [sys.executable, "-W", "always::ResourceWarning", "-c",
             "import tau_coding.taumain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("ResourceWarning", result.stderr)


if __name__ == "__main__":
    unittest.main()
