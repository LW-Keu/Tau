"""Streamlit 上传功能纯逻辑(零 streamlit 依赖,可独立单测)。
负责:落盘 / 文本提取 / 图片编码 / prompt 组装。UI 在 app_v4.py。"""
import os
from core.paths import TEMP

UPLOAD_DIR = TEMP / "uploads"
_TEXT_EXTS = {".py", ".md", ".txt", ".json", ".csv", ".log", ".xml", ".html",
              ".yaml", ".yml", ".toml", ".ini", ".sh", ".js", ".ts", ".sql"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".ico"}
TEXT_INJECT_MAX_BYTES = 200 * 1024
TEXT_INJECT_MAX_LINES = 5000
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_ATTACHMENTS = 10


def extract_text(path):
    """读 UTF-8 正文(errors=replace)。返回 (text, lines)。
    超过阈值(字节或行数)→ text=None(不注入,交 agent 用 file_read 分段读)。"""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    lines = len(text.splitlines()) or (0 if text == "" else 1)
    if len(text.encode('utf-8')) > TEXT_INJECT_MAX_BYTES or lines > TEXT_INJECT_MAX_LINES:
        return None, lines
    return text, lines


def read_image_b64(path):
    """图片字节 → data URI(供 images 多模态通道)。零 PIL 依赖。"""
    import base64
    ext = os.path.splitext(path)[1].lower().lstrip('.') or 'png'
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return f"data:{mime};base64,{b64}"
