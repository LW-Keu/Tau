"""Stage 3: /continue history replay consumes structured event logs.

Verifies that extract_ui_messages rebuilds UI messages from `.events.jsonl`
instead of reverse-engineering rendered strings from the Prompt/Response log.
"""
import json
import os
import tempfile
import unittest

from tau_agent.events import (
    AssistantTextChunk,
    AssistantTextDone,
    ToolCallStart,
    ToolOutputChunk,
    ToolOutputEnd,
    ToolOutputStart,
    TurnEnded,
    TurnStarted,
    event_to_json,
)
from apps.common.continue_cmd import extract_ui_messages


class TestExtractUiMessagesFromEvents(unittest.TestCase):
    def _write_logs(self, txt_content, events):
        tmp = tempfile.mkdtemp()
        base = os.path.join(tmp, "model_responses_123")
        txt_path = base + ".txt"
        events_path = base + ".events.jsonl"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)
        with open(events_path, "w", encoding="utf-8") as f:
            for event in events:
                f.write(event_to_json(event) + "\n")
        return txt_path

    def _prompt(self, text):
        return json.dumps(
            {"role": "user", "content": [{"type": "text", "text": text}]},
            ensure_ascii=False,
            indent=2,
        )

    def test_no_events_file_returns_empty(self):
        tmp = tempfile.mkdtemp()
        txt = os.path.join(tmp, "model_responses_999.txt")
        with open(txt, "w", encoding="utf-8") as f:
            f.write("")
        self.assertEqual(extract_ui_messages(txt), [])

    def test_single_user_assistant_round(self):
        path = self._write_logs(
            f"=== Prompt ===\n{self._prompt('hello')}\n=== Response ===\n[{self._assistant_repr('Hi there')}]\n",
            [
                TurnStarted(1),
                AssistantTextChunk("Hi there"),
                AssistantTextDone(),
                TurnEnded({"result": "CURRENT_TASK_DONE"}),
            ],
        )
        msgs = extract_ui_messages(path)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0], {"role": "user", "content": "hello"})
        self.assertEqual(msgs[1]["role"], "assistant")
        self.assertIn("Hi there", msgs[1]["content"])
        self.assertIn("LLM Running (Turn 1)", msgs[1]["content"])

    def test_user_round_with_tool_call(self):
        path = self._write_logs(
            f"=== Prompt ===\n{self._prompt('read it')}\n=== Response ===\n[{self._assistant_repr('OK')}]\n",
            [
                TurnStarted(1),
                AssistantTextChunk("OK"),
                AssistantTextDone(),
                ToolCallStart("file_read", {"path": "/tmp/x"}, tool_id="t1"),
                ToolOutputStart(),
                ToolOutputChunk("file contents"),
                ToolOutputEnd(),
                TurnEnded({"result": "CURRENT_TASK_DONE"}),
            ],
        )
        msgs = extract_ui_messages(path)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0], {"role": "user", "content": "read it"})
        assistant = msgs[1]["content"]
        self.assertIn("file_read", assistant)
        self.assertIn("file contents", assistant)
        self.assertIn("`````", assistant)

    def test_auto_continuation_concatenates_into_one_assistant(self):
        """Two LLM calls with no real user prompt in between become one assistant bubble."""
        txt = (
            f"=== Prompt ===\n{self._prompt('start')}\n"
            f"=== Response ===\n[{self._assistant_repr('first')}]\n"
            "=== Prompt ===\n{\"role\": \"user\", \"content\": [{\"type\": \"tool_result\"}]}\n"
            f"=== Response ===\n[{self._assistant_repr('second')}]\n"
        )
        path = self._write_logs(
            txt,
            [
                TurnStarted(1),
                AssistantTextChunk("first"),
                AssistantTextDone(),
                TurnEnded({"result": "CURRENT_TASK_DONE"}),
                TurnStarted(2),
                AssistantTextChunk("second"),
                AssistantTextDone(),
                TurnEnded({"result": "CURRENT_TASK_DONE"}),
            ],
        )
        msgs = extract_ui_messages(path)
        self.assertEqual(len(msgs), 2)  # one user + one assistant
        self.assertEqual(msgs[0], {"role": "user", "content": "start"})
        self.assertEqual(msgs[1]["role"], "assistant")
        assistant = msgs[1]["content"]
        self.assertIn("Turn 1", assistant)
        self.assertIn("Turn 2", assistant)
        self.assertIn("first", assistant)
        self.assertIn("second", assistant)

    def _assistant_repr(self, text):
        return json.dumps(
            {"role": "assistant", "content": [{"type": "text", "text": text}]},
            ensure_ascii=False,
        )


if __name__ == "__main__":
    unittest.main()
