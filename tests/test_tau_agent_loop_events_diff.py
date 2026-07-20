"""Stage 1 golden diff: agent_runner_loop (event-backed) vs the legacy string loop.

For identical mock inputs, the new agent_runner_loop — which renders
agent_runner_loop_events via render_events — must yield the exact same
dict+str sequence as _agent_runner_loop_str_legacy (the pre-refactor loop body,
preserved as the golden reference).

Covers: verbose text+tool, the tool-yields-vs-not fence boundary, no_tool
task-done, should_exit, task_mode header, non-verbose path, and yield_info
dict interleaving.
"""
import json
import tempfile
import unittest

from tau_agent.agent_loop import (
    StepOutcome,
    _agent_runner_loop_str_legacy,
    agent_runner_loop,
)
from tau_agent.handler import TauHandler


class _FakeFunction:
    def __init__(self, name, args):
        self.name = name
        self.arguments = json.dumps(args)


class _FakeToolCall:
    def __init__(self, name, args, tid="t1"):
        self.function = _FakeFunction(name, args)
        self.id = tid


class _FakeResponse:
    def __init__(self, content, tool_calls=None, thinking=""):
        self.content = content
        self.tool_calls = tool_calls or []
        self.thinking = thinking


class FakeClient:
    """LLM client mock. chat() yields scripted chunks then returns the response."""

    def __init__(self, turns):
        self._turns = [(chunks, resp) for chunks, resp in turns]
        self.last_tools = ""

    def chat(self, messages, tools):
        chunks, resp = self._turns.pop(0)
        for c in chunks:
            yield c
        return resp


class _FakeHandler(TauHandler):
    """TauHandler + a scriptable fake_tool for deterministic dispatch."""

    def do_fake_tool(self, args, response):
        for chunk in args.get("_yield", []):
            yield chunk
        return StepOutcome(
            args.get("_data"),
            next_prompt=args.get("_next_prompt", "\n"),
            should_exit=args.get("_exit", False),
        )


def _fake_host(task_dir):
    class _H:
        pass
    h = _H()
    h.task_dir = task_dir
    h.verbose = True
    h._turn_end_hooks = {}
    h.history_snapshot = lambda: "[]"
    return h


class TestAgentRunnerLoopEventDiff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _run_both(self, turns, max_turns, verbose=True, yield_info=True, task_dir=None):
        host1 = _fake_host(task_dir)
        h1 = _FakeHandler(host1, last_history=[], cwd=self.tmp)
        legacy = list(_agent_runner_loop_str_legacy(
            FakeClient(turns), "sys", "u", h1, [], max_turns=max_turns,
            verbose=verbose, yield_info=yield_info))
        host2 = _fake_host(task_dir)
        h2 = _FakeHandler(host2, last_history=[], cwd=self.tmp)
        new = list(agent_runner_loop(
            FakeClient(turns), "sys", "u", h2, [], max_turns=max_turns,
            verbose=verbose, yield_info=yield_info))
        return legacy, new

    def test_verbose_text_plus_tool_matches(self):
        turns = [(
            ["Hello", " world"],
            _FakeResponse("Hello world", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["[Action]\n", "out"], "_data": {"r": 1}, "_next_prompt": "\n"})]),
        )]
        legacy, new = self._run_both(turns, max_turns=1, verbose=True, yield_info=True)
        self.assertEqual(legacy, new)

    def test_verbose_tool_that_does_not_yield_matches(self):
        # Fence boundary: a tool returning without yielding must emit no
        # ToolOutputStart/Chunk/End — legacy gates :85/:87 behind v=next(gen).
        turns = [(
            ["Hi"],
            _FakeResponse("Hi", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": [], "_data": None, "_next_prompt": "\n"})]),
        )]
        legacy, new = self._run_both(turns, max_turns=1, verbose=True, yield_info=True)
        self.assertEqual(legacy, new)

    def test_verbose_no_tool_task_done_matches(self):
        # No tool_calls → no_tool → do_no_tool returns next_prompt=None → task done break.
        turns = [(["done text"], _FakeResponse("done text"))]
        legacy, new = self._run_both(turns, max_turns=5, verbose=True, yield_info=True)
        self.assertEqual(legacy, new)

    def test_verbose_tool_should_exit_matches(self):
        turns = [(
            ["x"],
            _FakeResponse("x", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["out\n"], "_data": {"ok": 1}, "_exit": True})]),
        )]
        legacy, new = self._run_both(turns, max_turns=5, verbose=True, yield_info=True)
        self.assertEqual(legacy, new)

    def test_task_mode_header_matches(self):
        # task_dir set → "Turn N ..." header (agent_loop.py:52).
        turns = [(
            ["x"],
            _FakeResponse("x", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["o"], "_next_prompt": "\n"})]),
        )]
        legacy, new = self._run_both(turns, max_turns=1, verbose=True, yield_info=True, task_dir=self.tmp)
        self.assertEqual(legacy, new)

    def test_non_verbose_path_matches(self):
        # Non-verbose: _clean_content whole output + compact tool header + exhaust (no fence).
        turns = [(
            ["Hello world"],
            _FakeResponse("Hello world", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["tool output\n"], "_data": {"d": 1}, "_next_prompt": "\n"})]),
        )]
        legacy, new = self._run_both(turns, max_turns=1, verbose=False, yield_info=False)
        self.assertEqual(legacy, new)

    def test_yield_info_dict_interleaving_matches(self):
        # yield_info must still emit {'turn': N} before the header (legacy :54).
        turns = [(
            ["a"],
            _FakeResponse("a", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["o"], "_next_prompt": "\n"})]),
        )]
        legacy, new = self._run_both(turns, max_turns=1, verbose=True, yield_info=True)
        self.assertEqual(legacy, new)
        # Confirm the dict is actually present (not just equal-but-empty).
        self.assertTrue(any(isinstance(x, dict) and x.get("turn") == 1 for x in new))


if __name__ == "__main__":
    unittest.main()
