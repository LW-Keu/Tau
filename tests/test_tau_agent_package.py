import importlib.util
import unittest


class TestTauAgentPackage(unittest.TestCase):

    def test_runtime_symbols_come_from_tau_agent(self):
        from tau_agent.agent_loop import BaseHandler, StepOutcome
        from tau_agent.handler import TauHandler

        self.assertEqual(BaseHandler.__module__, "tau_agent.agent_loop")
        self.assertEqual(StepOutcome.__module__, "tau_agent.agent_loop")
        self.assertEqual(TauHandler.__module__, "tau_agent.handler")

    def test_tool_symbols_come_from_tau_agent(self):
        from tau_agent.tools.code_run import code_run
        from tau_agent.tools.file_io import file_read
        from tau_agent.tools.utils import smart_format
        from tau_agent.tools.web import web_scan

        self.assertEqual(code_run.__module__, "tau_agent.tools.code_run")
        self.assertEqual(file_read.__module__, "tau_agent.tools.file_io")
        self.assertEqual(smart_format.__module__, "tau_agent.tools.utils")
        self.assertEqual(web_scan.__module__, "tau_agent.tools.web")

    def test_old_core_modules_are_removed(self):
        for module in ("core.agent_loop", "core.handler", "core.tools"):
            with self.subTest(module=module):
                self.assertIsNone(importlib.util.find_spec(module))


if __name__ == "__main__":
    unittest.main()
