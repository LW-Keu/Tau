import importlib.util
import unittest


def find_spec(name):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


class TestTauAgentPackage(unittest.TestCase):

    def test_runtime_symbols_come_from_tau_agent(self):
        from tau_agent.agent_loop import BaseHandler, StepOutcome
        from tau_agent.handler import TauHandler

        self.assertEqual(BaseHandler.__module__, "tau_agent.agent_loop")
        self.assertEqual(StepOutcome.__module__, "tau_agent.agent_loop")
        self.assertEqual(TauHandler.__module__, "tau_agent.handler")

    def test_tool_symbols_come_from_tau_agent(self):
        from tau_agent.tools.code_run import code_run, ask_user
        from tau_agent.tools.file_io import file_read, file_patch
        from tau_agent.tools.utils import smart_format, format_error, consume_file, get_global_memory
        from tau_agent.tools.web import web_scan, web_execute_js, first_init_driver

        cases = [
            (code_run, "tau_agent.tools.code_run"),
            (ask_user, "tau_agent.tools.code_run"),
            (file_read, "tau_agent.tools.file_io"),
            (file_patch, "tau_agent.tools.file_io"),
            (smart_format, "tau_agent.tools.utils"),
            (format_error, "tau_agent.tools.utils"),
            (consume_file, "tau_agent.tools.utils"),
            (get_global_memory, "tau_agent.tools.utils"),
            (web_scan, "tau_agent.tools.web"),
            (web_execute_js, "tau_agent.tools.web"),
            (first_init_driver, "tau_agent.tools.web"),
        ]
        for symbol, expected in cases:
            with self.subTest(symbol=symbol.__name__):
                self.assertEqual(symbol.__module__, expected)

    def test_old_core_modules_are_removed(self):
        for module in ("core.agent_loop", "core.handler", "core.tools"):
            with self.subTest(module=module):
                self.assertIsNone(find_spec(module))


if __name__ == "__main__":
    unittest.main()
