import queue

from tau_coding.taumain import Tau


def test_registered_slash_command_dispatches_without_patching():
    original = Tau._handle_slash_cmd
    calls = []

    def command(agent, raw, events):
        calls.append((agent, raw, events))
        return "handled"

    Tau.register_slash_command("test-command", command)
    agent = object.__new__(Tau)
    events = queue.Queue()

    assert agent._handle_slash_cmd("/test-command value", events) == "handled"
    assert calls == [(agent, "/test-command value", events)]
    assert Tau._handle_slash_cmd is original


def test_unregistered_text_and_slash_commands_pass_through():
    agent = object.__new__(Tau)
    events = queue.Queue()

    assert agent._handle_slash_cmd("hello", events) == "hello"
    assert agent._handle_slash_cmd("/unknown", events) == "/unknown"
