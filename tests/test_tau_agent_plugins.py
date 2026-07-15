import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


def _find_spec(name):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


class TestTauAgentPluginBoundary(unittest.TestCase):
    def test_hook_symbols_come_from_tau_agent(self):
        from tau_agent.plugins.hooks import discover_and_load, register, trigger

        for exported in (discover_and_load, register, trigger):
            self.assertEqual(exported.__module__, "tau_agent.plugins.hooks")

    def test_old_plugins_package_is_removed(self):
        for module in ("plugins", "plugins.hooks", "plugins.langfuse_tracing"):
            with self.subTest(module=module):
                self.assertIsNone(_find_spec(module))


class TestHookRegistry(unittest.TestCase):
    def setUp(self):
        from tau_agent.plugins import hooks

        self.hooks = hooks
        self.hooks.clear()

    def tearDown(self):
        self.hooks.clear()

    def test_trigger_threads_context_in_registration_order(self):
        seen = []

        @self.hooks.register("event")
        def first(ctx):
            seen.append(("first", ctx["value"]))
            return {"value": ctx["value"] + 1}

        @self.hooks.register("event")
        def second(ctx):
            seen.append(("second", ctx["value"]))
            return {"value": ctx["value"] * 2}

        self.assertTrue(self.hooks.has("event"))
        self.assertEqual(self.hooks.trigger("event", {"value": 3}), {"value": 8})
        self.assertEqual(seen, [("first", 3), ("second", 4)])

        self.hooks.unregister("event", first)
        self.assertEqual(self.hooks.trigger("event", {"value": 3}), {"value": 6})

    def test_clear_removes_one_event_or_the_whole_registry(self):
        @self.hooks.register("first")
        def first(ctx):
            return ctx

        @self.hooks.register("second")
        def second(ctx):
            return ctx

        self.hooks.clear("first")
        self.assertFalse(self.hooks.has("first"))
        self.assertTrue(self.hooks.has("second"))

        self.hooks.clear()
        self.assertFalse(self.hooks.has("second"))

    def test_callback_error_does_not_skip_later_callbacks(self):
        called = []

        @self.hooks.register("event")
        def broken(ctx):
            raise RuntimeError("boom")

        @self.hooks.register("event")
        def later(ctx):
            called.append(ctx["value"])

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = self.hooks.trigger("event", {"value": 7})

        self.assertEqual(result, {"value": 7})
        self.assertEqual(called, [7])
        self.assertIn("[hooks] event callback error: boom", stderr.getvalue())

    def test_explicit_plugin_directory_loads_by_package_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "fixture_plugins"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "demo.py").write_text(
                "from tau_agent.plugins.hooks import register\n"
                "@register('external')\n"
                "def callback(ctx):\n"
                "    return {'loaded': ctx['value']}\n",
                encoding="utf-8",
            )

            try:
                self.hooks.discover_and_load(str(package))
                self.assertEqual(
                    self.hooks.trigger("external", {"value": 9}),
                    {"loaded": 9},
                )
                self.assertIn("fixture_plugins.demo", sys.modules)
            finally:
                if tmp in sys.path:
                    sys.path.remove(tmp)
                for name in list(sys.modules):
                    if name == "fixture_plugins" or name.startswith("fixture_plugins."):
                        del sys.modules[name]


if __name__ == "__main__":
    unittest.main()
