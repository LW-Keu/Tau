import os, importlib, unittest
from pathlib import Path

class TestTauPaths(unittest.TestCase):
    def test_constants_point_to_existing_repo_dirs(self):
        import tau_paths as paths
        self.assertTrue(paths.ASSETS.is_dir())
        self.assertTrue(paths.MEMORY.is_dir())
        self.assertEqual(paths.ASSETS, paths.TAU_HOME / "assets")
        self.assertEqual(paths.MEMORY, paths.TAU_HOME / "memories")

    def test_tau_home_points_to_repo_root_not_src(self):
        # tau_paths.py 位于 src/ 下，parents[1] 应回溯到仓库根（含 pyproject.toml），
        # 而非误指 src/（ADR 0001 + tau-coding-package-migration-design:67-70）。
        # 防回归：从 tau_coding/paths.py (parents[2]) 剥离到 src/tau_paths.py 时
        # 若漏改层级，TAU_HOME 会指向仓库根的父目录。
        import tau_paths
        self.assertNotEqual(tau_paths.TAU_HOME.name, "src")
        self.assertTrue((tau_paths.TAU_HOME / "pyproject.toml").is_file())

    def test_tau_home_env_override(self):
        os.environ["TAU_HOME"] = "/tmp/tau_home_probe"
        import tau_paths as paths
        importlib.reload(paths)
        self.assertEqual(paths.TAU_HOME, Path("/tmp/tau_home_probe"))
        del os.environ["TAU_HOME"]
        importlib.reload(paths)
