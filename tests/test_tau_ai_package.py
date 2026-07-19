import importlib.util
import unittest
from pathlib import Path


def find_spec(name):
    try:
        return importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return None


class TestTauAiPackage(unittest.TestCase):

    def test_facade_exports_come_from_tau_ai(self):
        from tau_ai import BaseSession, ClaudeSession, LLMSession, ToolClient

        for exported in (BaseSession, ClaudeSession, LLMSession, ToolClient):
            self.assertTrue(exported.__module__.startswith("tau_ai."))

    def test_facade_public_api_imports(self):
        # 公共 API 全量从 facade 可导入（tau_ai 包迁移后无 compat shim）
        from tau_ai import (
            reload_taukeys,
            BaseSession, LLMSession, ClaudeSession, NativeClaudeSession, NativeOAISession,
            ToolClient, NativeToolClient, MixinSession,
            resolve_session, resolve_client, fast_ask,
            auto_make_url, openai_tools_to_claude,
            MockFunction, MockToolCall, MockResponse, tryparse,
        )
        # 载重私有符号保留在 facade 上供包外消费者使用：
        # tau_agent.plugins.langfuse_tracing._load_taukeys / apps/common/cost_tracker._record_usage
        from tau_ai import _load_taukeys, _record_usage

    def test_internal_symbols_live_in_submodules(self):
        # 内部符号必须从其定义子模块导入（锁定 tau_ai 包迁移回归）
        from tau_ai import _record_usage
        from tau_ai.trim import compress_history_tags
        from tau_ai.transport import _stream_with_retry, _write_llm_log, auto_make_url
        from tau_ai.convert import _fix_messages, _msgs_claude2oai, openai_tools_to_claude
        from tau_ai.response import MockResponse, MockToolCall, tryparse
        from tau_ai.session import BaseSession
        from tau_ai.providers.claude import ClaudeSession, NativeClaudeSession
        from tau_ai.providers.openai import LLMSession, NativeOAISession
        from tau_ai.clients import ToolClient, NativeToolClient, MixinSession, resolve_client
        cases = [
            (compress_history_tags, "tau_ai.trim"),
            (auto_make_url, "tau_ai.transport"),
            (_stream_with_retry, "tau_ai.transport"),
            (_record_usage, "tau_ai.transport"),
            (_write_llm_log, "tau_ai.transport"),
            (_fix_messages, "tau_ai.convert"),
            (_msgs_claude2oai, "tau_ai.convert"),
            (openai_tools_to_claude, "tau_ai.convert"),
            (MockResponse, "tau_ai.response"),
            (MockToolCall, "tau_ai.response"),
            (tryparse, "tau_ai.response"),
            (BaseSession, "tau_ai.session"),
            (ClaudeSession, "tau_ai.providers.claude"),
            (NativeClaudeSession, "tau_ai.providers.claude"),
            (LLMSession, "tau_ai.providers.openai"),
            (NativeOAISession, "tau_ai.providers.openai"),
            (ToolClient, "tau_ai.clients"),
            (NativeToolClient, "tau_ai.clients"),
            (MixinSession, "tau_ai.clients"),
            (resolve_client, "tau_ai.clients"),
        ]
        for symbol, suffix in cases:
            with self.subTest(symbol=symbol.__name__):
                self.assertTrue(
                    symbol.__module__.endswith(suffix),
                    f"{symbol.__name__}: expected module ending {suffix!r}, "
                    f"got {symbol.__module__!r}")

    def test_core_llm_is_removed(self):
        self.assertIsNone(find_spec("core.llm"))

    def test_legacy_key_json_is_beside_keys_module(self):
        import tau_ai.keys

        legacy = Path(tau_ai.keys.__file__).with_name("taukey.json")
        self.assertTrue(legacy.is_file(), legacy)


if __name__ == "__main__":
    unittest.main()
