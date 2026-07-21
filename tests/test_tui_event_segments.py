"""Stage 2b2: verify tui's event-based turn splitting without spinning up Textual.

These tests exercise the module-level helpers _event_turns and _turn_title,
which replaced fold_turns() for the main UI path.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.tui.app import _event_turns, _turn_title
from tau_agent.events import (
    AssistantTextChunk,
    AssistantTextDone,
    ToolCallStart,
    ToolOutputChunk,
    ToolOutputEnd,
    ToolOutputStart,
    TurnEnded,
    TurnStarted,
)


class TestTuiEventSegments(unittest.TestCase):
    def test_event_turns_splits_on_turn_started(self):
        events = [
            TurnStarted(1),
            AssistantTextChunk("hello"),
            AssistantTextDone(),
            TurnStarted(2),
            AssistantTextChunk("world"),
            TurnEnded({"result": "MAX_TURNS_EXCEEDED"}),
        ]
        turns = _event_turns(events)
        self.assertEqual(len(turns), 2)
        self.assertIn("hello", turns[0])
        self.assertIn("world", turns[1])
        # TurnEnded should not add text.
        self.assertNotIn("MAX_TURNS_EXCEEDED", turns[1])

    def test_event_turns_tool_content_inside_turn(self):
        events = [
            TurnStarted(1),
            AssistantTextChunk("use tool"),
            AssistantTextDone(),
            ToolCallStart("file_read", {"path": "/x"}),
            ToolOutputStart(),
            ToolOutputChunk("file content"),
            ToolOutputEnd(),
            TurnEnded({"result": "EXITED"}),
        ]
        turns = _event_turns(events)
        self.assertEqual(len(turns), 1)
        self.assertIn("use tool", turns[0])
        self.assertIn("file_read", turns[0])
        self.assertIn("file content", turns[0])

    def test_turn_title_prefers_summary(self):
        text = "<summary>Did the thing</summary>\nrest of turn"
        self.assertEqual(_turn_title(text), "Did the thing")

    def test_turn_title_falls_back_to_first_line(self):
        text = "first line of turn\nmore"
        self.assertEqual(_turn_title(text), "first line of turn")


if __name__ == "__main__":
    unittest.main()
