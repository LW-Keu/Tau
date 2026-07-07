"""upload_utils 纯逻辑测试。"""
import os, sys, pathlib
_STREAMLIT_DIR = pathlib.Path(__file__).resolve().parent.parent / 'apps' / 'web' / 'streamlit'
if str(_STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(_STREAMLIT_DIR))


def test_extract_text_under_threshold(tmp_path):
    from upload_utils import extract_text
    f = tmp_path / "a.txt"
    f.write_text("line1\nline2\n", encoding='utf-8')
    text, lines = extract_text(str(f))
    assert text == "line1\nline2\n"
    assert lines == 2


def test_extract_text_over_threshold_lines(tmp_path):
    from upload_utils import extract_text, TEXT_INJECT_MAX_LINES
    f = tmp_path / "big.txt"
    f.write_text("x\n" * (TEXT_INJECT_MAX_LINES + 1000), encoding='utf-8')
    text, lines = extract_text(str(f))
    assert text is None              # 超阈值不注入
    assert lines == TEXT_INJECT_MAX_LINES + 1000


def test_read_image_b64_data_uri(tmp_path):
    from upload_utils import read_image_b64
    # 1×1 PNG(minimal,无需 PIL 生成)
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c63000100000005000100")
    p = tmp_path / "x.png"
    p.write_bytes(png)
    uri = read_image_b64(str(p))
    assert uri.startswith("data:image/png;base64,")


def test_read_image_b64_jpeg_mime(tmp_path):
    from upload_utils import read_image_b64
    p = tmp_path / "x.jpg"
    p.write_bytes(b"\xff\xd8\xff\xe0fake")
    uri = read_image_b64(str(p))
    assert uri.startswith("data:image/jpeg;base64,")


class _FakeUF:
    """模拟 streamlit UploadedFile:.name + .getvalue()。"""
    def __init__(self, name, data):
        self.name = name
        self._d = data
    def getvalue(self):
        return self._d


def test_save_upload_text_file(tmp_path):
    from upload_utils import save_upload
    uf = _FakeUF("demo.py", b"print('hi')\n")
    att = save_upload(uf, upload_dir=tmp_path)
    assert att["kind"] == "text"
    assert att["name"] == "demo.py"
    assert att["text"] == "print('hi')\n"
    assert att["lines"] == 1
    assert os.path.exists(att["path"])


def test_save_upload_binary_file(tmp_path):
    from upload_utils import save_upload
    uf = _FakeUF("a.zip", b"\x50\x4b\x03\x04binary")
    att = save_upload(uf, upload_dir=tmp_path)
    assert att["kind"] == "binary"
    assert att["text"] is None and att["img_b64"] is None
    assert os.path.exists(att["path"])


def test_save_upload_image_file(tmp_path):
    from upload_utils import save_upload
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c63000100000005000100")
    uf = _FakeUF("x.png", png)
    att = save_upload(uf, upload_dir=tmp_path)
    assert att["kind"] == "image"
    assert att["img_b64"].startswith("data:image/png;base64,")
    # thumb_b64:有 PIL 则非 None,无 PIL 则 None(回退原图,两种都合法)
    if att["thumb_b64"] is not None:
        assert att["thumb_b64"].startswith("data:image/jpeg;base64,")


def test_save_upload_oversize_rejected(tmp_path):
    from upload_utils import save_upload, MAX_FILE_SIZE
    uf = _FakeUF("big.bin", b"x" * (MAX_FILE_SIZE + 1))
    assert save_upload(uf, upload_dir=tmp_path) is None


def test_save_upload_path_traversal_sanitized(tmp_path):
    from upload_utils import save_upload
    uf = _FakeUF("../../etc/passwd", b"x")
    att = save_upload(uf, upload_dir=tmp_path)
    # 落盘文件名只保留 basename,落在 upload_dir 内
    assert att["path"].startswith(str(tmp_path))
    assert ".." not in os.path.relpath(att["path"], tmp_path)


def test_save_upload_same_name_no_overwrite(tmp_path):
    from upload_utils import save_upload
    a = save_upload(_FakeUF("dup.py", b"a"), upload_dir=tmp_path)
    b = save_upload(_FakeUF("dup.py", b"bb"), upload_dir=tmp_path)
    assert a["path"] != b["path"]   # 时间戳+uuid 后缀保证不覆盖
    assert os.path.exists(a["path"]) and os.path.exists(b["path"])


def test_save_upload_non_utf8_degrades_to_binary(tmp_path):
    from upload_utils import save_upload
    # .txt 但内容是非法 UTF-8 字节 → 可打印率不足 → 降级 binary
    uf = _FakeUF("fake.txt", b"\xff\xfe\x00\x01\x02binary\xff")
    att = save_upload(uf, upload_dir=tmp_path)
    assert att["kind"] == "binary"
