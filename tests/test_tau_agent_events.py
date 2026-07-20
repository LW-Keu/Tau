"""Stage 0/1: typed event contract + default_render golden.

Validates that render_event reproduces agent_loop.py's current verbose string
output for each event type. Stage 1 checks the same golden against real
agent_runner_loop sessions (byte-for-byte diff vs the legacy string loop).

expected strings are built from get_pretty_json() dynamically so the args-fence
format stays in lockstep with agent_loop.py:37 — no hand-rolled JSON.
"""
import unittest

from tau_agent.agent_loop import get_pretty_json
from tau_agent.events import (
    AssistantTextChunk,
    AssistantTextDone,
    RawText,
    ToolCallStart,
    ToolOutputChunk,
    ToolOutputEnd,
    ToolOutputStart,
    TurnEnded,
    TurnStarted,
    render_event,
    render_events,
)


class TestRenderEvent(unittest.TestCase):
    def test_turn_started_default_verbose(self):
        self.assertEqual(
            render_event(TurnStarted(1)),
            "\n\n**LLM Running (Turn 1) ...**\n\n",
        )

    def test_turn_started_task_mode_shortens_header(self):
        # Mirrors agent_loop.py:52 — task_dir set → "Turn N ..." (no "LLM Running").
        self.assertEqual(
            render_event(TurnStarted(1, task_mode=True)),
            "\n\n**Turn 1 ...**\n\n",
        )

    def test_turn_started_non_verbose_drops_bold(self):
        self.assertEqual(
            render_event(TurnStarted(1), verbose=False),
            "\n\nLLM Running (Turn 1) ...\n\n",
        )

    def test_assistant_text_chunk_passthrough(self):
        self.assertEqual(render_event(AssistantTextChunk("Hello")), "Hello")

    def test_assistant_text_done_emits_blank_line(self):
        self.assertEqual(render_event(AssistantTextDone()), "\n\n")

    def test_tool_call_start_is_header_only(self):
        # Mirrors agent_loop.py:78 only (🛠️ header + 4-backtick args fence).
        # The 5-backtick output fence-open is a separate ToolOutputStart event,
        # because :85 is gated behind the tool actually yielding.
        out = render_event(ToolCallStart("file_read", {"path": "/x"}))
        pretty = get_pretty_json({"path": "/x"})
        expected = (
            "🛠️ Tool: `file_read`  📥 args:\n"
            "````text\n"
            f"{pretty}\n"
            "````\n"
        )
        self.assertEqual(out, expected)

    def test_tool_output_start_opens_fence(self):
        self.assertEqual(render_event(ToolOutputStart()), "`````\n")

    def test_tool_output_chunk_passthrough(self):
        self.assertEqual(render_event(ToolOutputChunk("[Action] Reading\n")), "[Action] Reading\n")

    def test_tool_output_end_closes_fence(self):
        self.assertEqual(render_event(ToolOutputEnd()), "`````\n")

    def test_raw_text_passthrough(self):
        self.assertEqual(render_event(RawText("anything\n")), "anything\n")

    def test_turn_ended_is_silent(self):
        self.assertEqual(render_event(TurnEnded({"result": "EXITED"})), "")

    def test_full_verbose_sequence_round_trips(self):
        # A canonical one-turn, one-tool verbose transcript reconstructed from
        # events must equal the string the current loop would yield.
        events = [
            TurnStarted(1),
            AssistantTextChunk("Hello"),
            AssistantTextChunk(" world"),
            AssistantTextDone(),
            ToolCallStart("file_read", {"path": "/x"}, tool_id="t1"),
            ToolOutputStart(),
            ToolOutputChunk("[Action] Reading\n"),
            ToolOutputChunk("content here"),
            ToolOutputEnd(),
            TurnEnded({"result": "CURRENT_TASK_DONE"}),
        ]
        out = "".join(render_events(events))
        pretty = get_pretty_json({"path": "/x"})
        expected = (
            "\n\n**LLM Running (Turn 1) ...**\n\n"
            "Hello world\n\n"
            "🛠️ Tool: `file_read`  📥 args:\n````text\n"
            f"{pretty}\n````\n"
            "`````\n"
            "[Action] Reading\ncontent here"
            "`````\n"
        )
        self.assertEqual(out, expected)


if __name__ == "__main__":
    unittest.main()
