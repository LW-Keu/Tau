import pytest

from tau_ai.clients import config_kind, resolve_session
from tau_ai.providers.claude import NativeClaudeSession
from tau_ai.providers.openai import NativeOAISession


def config(kind):
    return {
        "type": kind,
        "name": "test",
        "apikey": "key",
        "apibase": "https://example.test",
        "model": "model",
    }


def test_explicit_type_ignores_variable_name():
    assert isinstance(
        resolve_session("misleading_oai_config", config("native_claude")),
        NativeClaudeSession,
    )
    assert isinstance(
        resolve_session("misleading_claude_config", config("native_oai")),
        NativeOAISession,
    )


def test_arbitrary_variable_name_works_with_explicit_type():
    assert config_kind("primary", config("native_oai")) == "native_oai"


def test_legacy_variable_name_remains_supported():
    legacy = config("native_oai")
    legacy.pop("type")
    assert config_kind("native_oai_config", legacy) == "native_oai"


def test_unknown_explicit_type_fails_loudly():
    with pytest.raises(ValueError, match="unsupported type"):
        config_kind("primary", config("magic"))
