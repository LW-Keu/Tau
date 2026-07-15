import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_spec(name):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


class TestTauCodingPackage(unittest.TestCase):
    def test_new_modules_have_specs(self):
        modules = (
            "tau_coding.paths", "tau_coding.taumain", "tau_coding.cli",
            "tau_coding.reflect.autonomous", "tau_coding.reflect.goal_mode",
            "tau_coding.reflect.scheduler",
            "tau_coding.reflect.agent_team_worker",
        )
        for module in modules:
            with self.subTest(module=module):
                self.assertIsNotNone(find_spec(module))

    def test_old_packages_are_removed(self):
        for package in ("core", "tau_cli", "reflect"):
            with self.subTest(package=package):
                self.assertIsNone(find_spec(package))

    def test_console_entry_uses_tau_coding(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('tau = "tau_coding.cli:main"', text)
        self.assertNotIn('tau = "tau_cli.cli:main"', text)

    def test_package_import_is_lightweight(self):
        code = ("import sys,tau_coding; "
                "assert 'tau_coding.taumain' not in sys.modules; "
                "assert 'tau_ai' not in sys.modules; "
                "assert 'tau_agent' not in sys.modules")
        result = subprocess.run([sys.executable, "-c", code],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_import_is_lightweight(self):
        code = ("import sys,tau_coding.cli; "
                "assert 'tau_coding.taumain' not in sys.modules; "
                "assert 'tau_ai' not in sys.modules; "
                "assert 'tau_agent' not in sys.modules")
        result = subprocess.run([sys.executable, "-c", code],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_reflect_module_target_resolves(self):
        from tau_coding.taumain import _load_reflect
        module, source = _load_reflect("tau_coding.reflect.autonomous")
        self.assertEqual(module.__name__, "tau_coding.reflect.autonomous")
        self.assertEqual(Path(source).name, "autonomous.py")

    def test_reflect_file_target_resolves(self):
        from tau_coding.taumain import _load_reflect
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "custom_reflect.py"
            script.write_text("INTERVAL=1\nONCE=True\ndef check(): return None\n",
                              encoding="utf-8")
            module, source = _load_reflect(str(script))
        self.assertTrue(module.ONCE)
        self.assertEqual(Path(source), script.resolve())

    def test_launcher_scripts_are_package_files(self):
        scripts = ROOT / "src" / "tau_coding" / "scripts"
        expected = {"start.sh", "start_autonomous.sh", "start_scheduler.sh",
                    "stop_autonomous.sh", "stop_scheduler.sh",
                    "tau-cli-install.cmd", "tau_cli.cmd"}
        actual = {p.name for p in scripts.iterdir()
                  if p.suffix in {".sh", ".cmd"}}
        self.assertEqual(actual, expected)
