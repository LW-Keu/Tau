"""TauHandler runs without a concrete Tau instance (HostContext decoupling).

TauHandler historically depended on src/tau_coding/taumain.Tau as its parent.
These tests construct it against a lightweight FakeHost satisfying the
HostContext Protocol, then exercise every parent reach-back path:

* turn_end_callback — touches parent.task_dir and parent._turn_end_hooks.
* do_update_working_checkpoint — whose _get_anchor_prompt reads parent.verbose.
* do_code_run inline_eval — reads parent.history_snapshot() into the ns.

Stage B narrowed the protocol: FakeHost no longer fakes an llmclient, so the
suite proves the agent core needs only three attributes + history_snapshot().
The reverse test guards that ns['parent'] is gone (undocumented coupling surface
closed); the documented `handler` and `history` ns vars are unaffected.
"""
import json
import os
import tempfile
import unittest

from tau_agent.handler import HostContext, TauHandler


class FakeHost:
    """Minimal HostContext for unit tests — no LLM, no queue, no Tau."""

    def __init__(self, task_dir=None, verbose=False):
        self.task_dir = task_dir
        self.verbose = verbose
        self._turn_end_hooks = {}

    def history_snapshot(self):
        return json.dumps([{"role": "user", "content": "hi"}])


class _FakeResponse:
    def __init__(self, content):
        self.content = content
        self.thinking = ""


class TestHandlerHostDecoupling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.host = FakeHost(task_dir=self.tmp, verbose=False)
        self.handler = TauHandler(self.host, last_history=[], cwd=self.tmp)

    def test_host_context_protocol_is_exported(self):
        # Guards against someone silently replacing the Protocol with a plain class.
        self.assertTrue(getattr(HostContext, "_is_protocol", False))

    def test_handler_constructs_against_fake_host(self):
        self.assertIs(self.handler.parent, self.host)
        self.assertEqual(self.handler.cwd, os.path.abspath(self.tmp))
        self.assertEqual(self.handler.working, {})

    def test_turn_end_callback_runs_without_tau(self):
        # turn_end_callback is the parent-coupling hotspot — driving it to
        # completion with a FakeHost proves task_dir + _turn_end_hooks resolve
        # without a real Tau. The hook receives turn_end_callback's locals().
        fired = []
        self.host._turn_end_hooks["probe"] = lambda loc: fired.append(loc.get("turn"))
        resp = _FakeResponse("<summary>did the thing</summary>")
        self.handler.turn_end_callback(
            resp,
            tool_calls=[{"tool_name": "no_tool", "args": {}}],
            tool_results=[],
            turn=1,
            next_prompt="\n",
            exit_reason={},
        )
        self.assertEqual(fired, [1])
        self.assertIn("did the thing", self.handler.history_info[-1])

    def test_dispatch_runs_real_tool_without_tau(self):
        # do_update_working_checkpoint -> _get_anchor_prompt reads parent.verbose.
        # Default index=0 so skip=False, forcing the full anchor path.
        gen = self.handler.dispatch(
            "update_working_checkpoint",
            {"key_info": "remember this"},
            _FakeResponse(""),
        )
        list(gen)  # exhaust generator; return value discarded
        self.assertEqual(self.handler.working.get("key_info"), "remember this")

    def test_do_code_run_inline_eval_reads_host_history(self):
        # The inline_eval branch calls parent.history_snapshot() into ns['history'];
        # the eval code stashes it in _r.
        gen = self.handler.dispatch(
            "code_run",
            {"type": "python", "inline_eval": True, "code": "_r = history"},
            _FakeResponse(""),
        )
        outcome = None
        try:
            while True:
                next(gen)
        except StopIteration as e:
            outcome = e.value
        self.assertIsNotNone(outcome, "dispatch did not return a StepOutcome")
        self.assertIn("hi", str(outcome.data))

    def test_inline_eval_namespace_no_longer_exposes_parent(self):
        # Stage B removed ns['parent'] — eval code referencing it must fail
        # gracefully (caught by do_code_run's outer except), proving the
        # undocumented coupling surface is closed while `handler`/`history` stay.
        gen = self.handler.dispatch(
            "code_run",
            {"type": "python", "inline_eval": True, "code": "_r = parent"},
            _FakeResponse(""),
        )
        outcome = None
        try:
            while True:
                next(gen)
        except StopIteration as e:
            outcome = e.value
        self.assertIsNotNone(outcome)
        self.assertIn("Error", str(outcome.data))


if __name__ == "__main__":
    unittest.main()
