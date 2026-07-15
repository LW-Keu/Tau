import os
import sys
from pathlib import Path


STREAMLIT_DIR = Path(__file__).resolve().parents[1] / "apps" / "web" / "streamlit"
sys.path.insert(0, str(STREAMLIT_DIR))

from upload_utils import (MAX_FILE_SIZE, TEXT_INJECT_MAX_LINES, build_prompt,
                          extract_text, read_image_b64, save_upload)


class FakeUpload:
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def getvalue(self):
        return self.data


def test_extract_text_limits_lines(tmp_path):
    path = tmp_path / "large.txt"
    path.write_text("x\n" * (TEXT_INJECT_MAX_LINES + 1), encoding="utf-8")
    text, lines = extract_text(path)
    assert text is None
    assert lines == TEXT_INJECT_MAX_LINES + 1


def test_image_data_uri(tmp_path):
    path = tmp_path / "image.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0fake")
    assert read_image_b64(path).startswith("data:image/jpeg;base64,")


def test_save_upload_classifies_and_sanitizes_text(tmp_path):
    attachment = save_upload(FakeUpload("../../demo.py", b"print('hi')\n"), tmp_path)
    assert attachment["kind"] == "text"
    assert attachment["name"] == "demo.py"
    assert attachment["text"] == "print('hi')\n"
    assert os.path.commonpath([attachment["path"], tmp_path]) == str(tmp_path)


def test_save_upload_rejects_oversize(tmp_path):
    assert save_upload(FakeUpload("large.bin", b"x" * (MAX_FILE_SIZE + 1)), tmp_path) is None


def test_build_prompt_injects_text_and_references_binary(tmp_path):
    text_attachment = {"kind": "text", "name": "demo.py", "size": 10, "lines": 1,
                       "text": "print(1)", "path": str(tmp_path / "demo.py")}
    binary_attachment = {"kind": "binary", "name": "data.zip", "size": 2048,
                         "lines": None, "text": None,
                         "path": str(tmp_path / "uploads" / "data.zip")}
    prompt = build_prompt("review", [text_attachment, binary_attachment])
    assert "```py\nprint(1)\n```" in prompt
    assert "data.zip" in prompt and "file_read" in prompt
