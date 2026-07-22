"""Stage 1 golden snapshots: agent_runner_loop event-backed string adapter.

After the legacy string loop was removed, these scenarios are frozen as
snapshot fixtures. They guard against regressions in the event-to-string
adapter for verbose/non-verbose paths, tool-yield boundaries, task mode,
exit conditions, and yield_info dict interleaving.
"""
import json
import tempfile
import unittest

from tau_agent.agent_loop import StepOutcome, agent_runner_loop
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


# Frozen outputs captured from the legacy string loop before it was deleted.
VERBOSE_TEXT_PLUS_TOOL = [
    {"turn": 1},
    "\n\n**LLM Running (Turn 1) ...**\n\n",
    "Hello",
    " world",
    "\n\n",
    '🛠️ Tool: `fake_tool`  📥 args:\n````text\n{\n  "_yield": [\n    "[Action]\n",\n    "out"\n  ],\n  "_data": {\n    "r": 1\n  },\n  "_next_prompt": "\n"\n}\n````\n',
    "`````\n",
    "[Action]\n",
    "out",
    "`````\n",
]

VERBOSE_TOOL_NO_YIELD = [
    {"turn": 1},
    "\n\n**LLM Running (Turn 1) ...**\n\n",
    "Hi",
    "\n\n",
    '🛠️ Tool: `fake_tool`  📥 args:\n````text\n{\n  "_yield": [],\n  "_data": null,\n  "_next_prompt": "\n"\n}\n````\n',
]

VERBOSE_NO_TOOL_TASK_DONE = [
    {"turn": 1},
    "\n\n**LLM Running (Turn 1) ...**\n\n",
    "done text",
    "\n\n",
    "`````\n",
    "[Info] Final response to user.\n",
    "`````\n",
]

VERBOSE_TOOL_SHOULD_EXIT = [
    {"turn": 1},
    "\n\n**LLM Running (Turn 1) ...**\n\n",
    "x",
    "\n\n",
    '🛠️ Tool: `fake_tool`  📥 args:\n````text\n{\n  "_yield": [\n    "out\n"\n  ],\n  "_data": {\n    "ok": 1\n  },\n  "_exit": true\n}\n````\n',
    "`````\n",
    "out\n",
    "`````\n",
]

TASK_MODE_HEADER = [
    {"turn": 1},
    "\n\n**Turn 1 ...**\n\n",
    "x",
    "\n\n",
    '🛠️ Tool: `fake_tool`  📥 args:\n````text\n{\n  "_yield": [\n    "o"\n  ],\n  "_next_prompt": "\n"\n}\n````\n',
    "`````\n",
    "o",
    "`````\n",
]

NON_VERBOSE = [
    "\n\nLLM Running (Turn 1) ...\n\n",
    "Hello world\n",
    '🛠️ fake_tool({"_yield": ["tool output\\n"], "_data": {"d": 1}, "_next_prompt": "\\n"})\n\n\n',
]

YIELD_INFO_INTERLEAVING = [
    {"turn": 1},
    "\n\n**LLM Running (Turn 1) ...**\n\n",
    "a",
    "\n\n",
    '🛠️ Tool: `fake_tool`  📥 args:\n````text\n{\n  "_yield": [\n    "o"\n  ],\n  "_next_prompt": "\n"\n}\n````\n',
    "`````\n",
    "o",
    "`````\n",
]


class TestAgentRunnerLoopEventSnapshots(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _run(self, turns, max_turns, verbose=True, yield_info=True, task_dir=None):
        host = _fake_host(task_dir)
        h = _FakeHandler(host, last_history=[], cwd=self.tmp)
        return list(
            agent_runner_loop(
                FakeClient(turns),
                "sys",
                "u",
                h,
                [],
                max_turns=max_turns,
                verbose=verbose,
                yield_info=yield_info,
            )
        )

    def test_verbose_text_plus_tool_matches(self):
        turns = [(
            ["Hello", " world"],
            _FakeResponse("Hello world", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["[Action]\n", "out"], "_data": {"r": 1}, "_next_prompt": "\n"})]),
        )]
        self.assertEqual(self._run(turns, max_turns=1), VERBOSE_TEXT_PLUS_TOOL)

    def test_verbose_tool_that_does_not_yield_matches(self):
        # Fence boundary: a tool returning without yielding must emit no
        # ToolOutputStart/Chunk/End — legacy gated :85/:87 behind v=next(gen).
        turns = [(
            ["Hi"],
            _FakeResponse("Hi", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": [], "_data": None, "_next_prompt": "\n"})]),
        )]
        self.assertEqual(self._run(turns, max_turns=1), VERBOSE_TOOL_NO_YIELD)

    def test_verbose_no_tool_task_done_matches(self):
        # No tool_calls → no_tool → do_no_tool returns next_prompt=None → task done break.
        turns = [(["done text"], _FakeResponse("done text"))]
        self.assertEqual(self._run(turns, max_turns=5), VERBOSE_NO_TOOL_TASK_DONE)

    def test_verbose_tool_should_exit_matches(self):
        turns = [(
            ["x"],
            _FakeResponse("x", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["out\n"], "_data": {"ok": 1}, "_exit": True})]),
        )]
        self.assertEqual(self._run(turns, max_turns=5), VERBOSE_TOOL_SHOULD_EXIT)

    def test_task_mode_header_matches(self):
        # task_dir set → "Turn N ..." header (agent_loop.py:52).
        turns = [(
            ["x"],
            _FakeResponse("x", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["o"], "_next_prompt": "\n"})]),
        )]
        self.assertEqual(
            self._run(turns, max_turns=1, task_dir=self.tmp),
            TASK_MODE_HEADER,
        )

    def test_non_verbose_path_matches(self):
        # Non-verbose: _clean_content whole output + compact tool header + exhaust (no fence).
        turns = [(
            ["Hello world"],
            _FakeResponse("Hello world", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["tool output\n"], "_data": {"d": 1}, "_next_prompt": "\n"})]),
        )]
        self.assertEqual(
            self._run(turns, max_turns=1, verbose=False, yield_info=False),
            NON_VERBOSE,
        )

    def test_yield_info_dict_interleaving_matches(self):
        # yield_info must still emit {'turn': N} before the header (legacy :54).
        turns = [(
            ["a"],
            _FakeResponse("a", tool_calls=[_FakeToolCall(
                "fake_tool", {"_yield": ["o"], "_next_prompt": "\n"})]),
        )]
        out = self._run(turns, max_turns=1)
        self.assertEqual(out, YIELD_INFO_INTERLEAVING)
        # Confirm the dict is actually present (not just equal-but-empty).
        self.assertTrue(any(isinstance(x, dict) and x.get("turn") == 1 for x in out))


if __name__ == "__main__":
    unittest.main()
