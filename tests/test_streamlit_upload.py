import os
import queue
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_DIR = ROOT / "apps" / "web" / "streamlit"
APP_PATH = STREAMLIT_DIR / "app_v4.py"
sys.path.insert(0, str(STREAMLIT_DIR))

from upload_utils import (MAX_FILE_SIZE, TEXT_INJECT_MAX_LINES, build_prompt,
                          extract_text, read_image_b64, save_upload)


class FakeUpload:
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def getvalue(self):
        return self.data


class FakeAgent:
    llm_no = 0

    def __init__(self):
        self.llmclient = types.SimpleNamespace(last_tools="")

    def run(self):
        pass

    def list_llms(self):
        return [(0, "test", None)]

    def get_llm_name(self):
        return "test"

    def next_llm(self, index):
        self.llm_no = index

    def abort(self):
        pass

    def put_task(self, query, source, images):
        output = queue.Queue()
        output.put({"done": "ok"})
        return output


class StreamlitUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _attachment(self, name="demo.txt"):
        path = self.root / name
        path.write_text("attachment", encoding="utf-8")
        return {
            "id": "attachment-1", "name": name, "size": path.stat().st_size,
            "kind": "text", "path": str(path), "text": "attachment",
            "lines": 1, "img_b64": None, "thumb_b64": None,
        }

    def _app(self, attachment):
        app = AppTest.from_file(APP_PATH, default_timeout=5)
        app.run()
        app.session_state.pending_attachments = [attachment]
        return app.run()

    @contextmanager
    def _app_with_attachment(self, attachment):
        fake_module = types.SimpleNamespace(Tau=FakeAgent)
        with mock.patch.dict(sys.modules, {"tau_coding.taumain": fake_module}):
            yield self._app(attachment)

    def test_extract_text_limits_lines(self):
        path = self.root / "large.txt"
        path.write_text("x\n" * (TEXT_INJECT_MAX_LINES + 1), encoding="utf-8")
        text, lines = extract_text(path)
        self.assertIsNone(text)
        self.assertEqual(lines, TEXT_INJECT_MAX_LINES + 1)

    def test_image_data_uri(self):
        path = self.root / "image.jpg"
        path.write_bytes(b"\xff\xd8\xff\xe0fake")
        self.assertTrue(read_image_b64(path).startswith("data:image/jpeg;base64,"))

    def test_save_upload_classifies_and_sanitizes_text(self):
        attachment = save_upload(FakeUpload("../../demo.py", b"print('hi')\n"), self.root)
        self.assertEqual(attachment["kind"], "text")
        self.assertEqual(attachment["name"], "demo.py")
        self.assertEqual(attachment["text"], "print('hi')\n")
        self.assertEqual(os.path.commonpath([attachment["path"], self.root]), str(self.root))

    def test_save_upload_rejects_oversize(self):
        upload = FakeUpload("large.bin", b"x" * (MAX_FILE_SIZE + 1))
        self.assertIsNone(save_upload(upload, self.root))

    def test_build_prompt_injects_text_and_references_binary(self):
        text_attachment = {
            "kind": "text", "name": "demo.py", "size": 10, "lines": 1,
            "text": "print(1)", "path": str(self.root / "demo.py"),
        }
        binary_attachment = {
            "kind": "binary", "name": "data.zip", "size": 2048,
            "lines": None, "text": None,
            "path": str(self.root / "uploads" / "data.zip"),
        }
        prompt = build_prompt("review", [text_attachment, binary_attachment])
        self.assertIn("```py\nprint(1)\n```", prompt)
        self.assertIn("data.zip", prompt)
        self.assertIn("file_read", prompt)

    def test_entry_sends_attachment_without_text(self):
        attachment = self._attachment()
        with self._app_with_attachment(attachment) as app:
            send = next(button for button in app.button
                        if button.key == "btn_send_attachments")
            send.click().run()

        user = next(message for message in app.session_state.messages
                    if message["role"] == "user")
        self.assertEqual(user["content"], "请处理这些文件。")
        self.assertEqual(user["attachments"][0]["name"], "demo.txt")
        self.assertEqual(app.session_state.pending_attachments, [])

    def test_entry_sends_text_with_attachment(self):
        attachment = self._attachment()
        with self._app_with_attachment(attachment) as app:
            app.chat_input[0].set_value("review this").run()

        user = next(message for message in app.session_state.messages
                    if message["role"] == "user")
        self.assertEqual(user["content"], "review this")
        self.assertEqual(user["attachments"][0]["name"], "demo.txt")
        self.assertEqual(app.session_state.pending_attachments, [])

    def test_entry_deletes_pending_attachment(self):
        attachment = self._attachment()
        with self._app_with_attachment(attachment) as app:
            remove = next(button for button in app.button
                          if button.key == "rm_attachment-1")
            remove.click().run()

        self.assertFalse(Path(attachment["path"]).exists())
        self.assertEqual(app.session_state.pending_attachments, [])
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
