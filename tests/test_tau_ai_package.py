import importlib.util
import unittest
from pathlib import Path


class TestTauAiPackage(unittest.TestCase):

    def test_facade_exports_come_from_tau_ai(self):
        from tau_ai import BaseSession, ClaudeSession, LLMSession, ToolClient

        for exported in (BaseSession, ClaudeSession, LLMSession, ToolClient):
            self.assertTrue(exported.__module__.startswith("tau_ai."))

    def test_core_llm_is_removed(self):
        self.assertIsNone(importlib.util.find_spec("core.llm"))

    def test_legacy_key_json_is_beside_keys_module(self):
        import tau_ai.keys

        legacy = Path(tau_ai.keys.__file__).with_name("taukey.json")
        self.assertTrue(legacy.is_file(), legacy)


if __name__ == "__main__":
    unittest.main()
