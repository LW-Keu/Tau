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
