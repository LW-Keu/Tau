"""upload_utils 纯逻辑测试。"""
import sys, pathlib
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
