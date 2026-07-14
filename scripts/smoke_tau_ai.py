"""Smoke test: the tau_ai public API imports cleanly from the package facade,
and internal helpers import from their submodules (post-install, no compat shim).
taukeys lives on tau_ai.keys."""
# Public API — from the package facade.
from tau_ai import (
    reload_taukeys,
    BaseSession, LLMSession, ClaudeSession, NativeClaudeSession, NativeOAISession,
    ToolClient, NativeToolClient, MixinSession,
    resolve_session, resolve_client, fast_ask,
    auto_make_url, openai_tools_to_claude,
    MockFunction, MockToolCall, MockResponse, tryparse,
)
# Load-bearing privates kept on the facade for out-of-package consumers
# (plugins/langfuse_tracing._load_taukeys, apps/common/cost_tracker._record_usage).
from tau_ai import _load_taukeys, _record_usage
# Internals live in submodules — new code imports them there, not from the package.
from tau_ai.trim import compress_history_tags, trim_messages_history, safeprint
from tau_ai.transport import _stream_with_retry, _write_llm_log
from tau_ai.convert import (_fix_messages, _msgs_claude2oai, _to_responses_input,
                            _drop_unsigned_thinking, _ensure_thinking_blocks,
                            _stamp_oai_cache_markers, _prepare_oai_tools, _try_parse_tool_args)
from tau_ai.keys import taukeys
assert compress_history_tags.__module__.endswith('tau_ai.trim'), compress_history_tags.__module__
assert auto_make_url.__module__.endswith('tau_ai.transport'), auto_make_url.__module__
assert _stream_with_retry.__module__.endswith('tau_ai.transport'), _stream_with_retry.__module__
assert _record_usage.__module__.endswith('tau_ai.transport'), _record_usage.__module__
assert _write_llm_log.__module__.endswith('tau_ai.transport'), _write_llm_log.__module__
assert _fix_messages.__module__.endswith('tau_ai.convert'), _fix_messages.__module__
assert _msgs_claude2oai.__module__.endswith('tau_ai.convert'), _msgs_claude2oai.__module__
assert openai_tools_to_claude.__module__.endswith('tau_ai.convert'), openai_tools_to_claude.__module__
assert MockResponse.__module__.endswith('tau_ai.response'), MockResponse.__module__
assert MockToolCall.__module__.endswith('tau_ai.response'), MockToolCall.__module__
assert tryparse.__module__.endswith('tau_ai.response'), tryparse.__module__
assert BaseSession.__module__.endswith('tau_ai.session'), BaseSession.__module__
assert ClaudeSession.__module__.endswith('tau_ai.providers.claude'), ClaudeSession.__module__
assert NativeClaudeSession.__module__.endswith('tau_ai.providers.claude'), NativeClaudeSession.__module__
assert LLMSession.__module__.endswith('tau_ai.providers.openai'), LLMSession.__module__
assert NativeOAISession.__module__.endswith('tau_ai.providers.openai'), NativeOAISession.__module__
assert ToolClient.__module__.endswith('tau_ai.clients'), ToolClient.__module__
assert NativeToolClient.__module__.endswith('tau_ai.clients'), NativeToolClient.__module__
assert MixinSession.__module__.endswith('tau_ai.clients'), MixinSession.__module__
assert resolve_client.__module__.endswith('tau_ai.clients'), resolve_client.__module__

from core.paths import TAUKEY_PATH
print(f'[SMOKE-OK] taukey_path={TAUKEY_PATH} '
      f'taukeys_loaded={len(taukeys)} '
      f'private_load={_load_taukeys.__name__} '
      f'classes=({LLMSession.__name__},{ToolClient.__name__},{MixinSession.__name__}) '
      f'trim={compress_history_tags.__module__} '
      f'transport={auto_make_url.__module__} '
      f'convert={_fix_messages.__module__} '
      f'response={MockResponse.__module__} '
      f'session={BaseSession.__module__} '
      f'claude={ClaudeSession.__name__} '
      f'openai={LLMSession.__name__} '
      f'clients={ToolClient.__module__}')
