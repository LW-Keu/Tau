"""Pure upload helpers for the Streamlit UI."""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_r = os.path.abspath(os.path.dirname(__file__))
while _r != os.path.dirname(_r) and not os.path.exists(os.path.join(_r, 'pyproject.toml')):
    _r = os.path.dirname(_r)
if _r not in sys.path:
    sys.path.insert(0, _r)
# src-layout: tau_coding/tau_agent/tau_ai/tau_paths live under src/
_src = os.path.join(_r, 'src')
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

import time
import uuid

from tau_paths import TEMP


UPLOAD_DIR = TEMP / "uploads"
_TEXT_EXTS = {".py", ".md", ".txt", ".json", ".csv", ".log", ".xml", ".html",
              ".yaml", ".yml", ".toml", ".ini", ".sh", ".js", ".ts", ".sql"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".ico"}
TEXT_INJECT_MAX_BYTES = 200 * 1024
TEXT_INJECT_MAX_LINES = 5000
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_ATTACHMENTS = 10


def extract_text(path):
    """Read UTF-8 text, returning ``(None, lines)`` above injection limits."""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    lines = len(text.splitlines()) or (0 if text == "" else 1)
    if len(text.encode('utf-8')) > TEXT_INJECT_MAX_BYTES or lines > TEXT_INJECT_MAX_LINES:
        return None, lines
    return text, lines


def read_image_b64(path):
    """Return image bytes as a data URI without requiring Pillow."""
    import base64
    ext = os.path.splitext(path)[1].lower().lstrip('.') or 'png'
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return f"data:{mime};base64,{b64}"


def _printable_ratio(raw_bytes):
    if not raw_bytes:
        return 1.0
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return 0.0
    printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
    return printable / max(len(text), 1)


def _make_thumb(path, max_size=400, quality=70):
    try:
        import base64
        import io
        from PIL import Image
        image = Image.open(path)
        image.thumbnail((max_size, max_size))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        buffer = io.BytesIO()
        image.save(buffer, 'JPEG', quality=quality)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode('ascii')
    except Exception:
        return None


def save_upload(upload, upload_dir=UPLOAD_DIR):
    """Validate and persist an upload, returning attachment metadata."""
    try:
        content = upload.getvalue()
    except Exception:
        return None
    if len(content) > MAX_FILE_SIZE:
        return None
    safe_name = os.path.basename(upload.name)
    timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    filename = f"{timestamp}__{uuid.uuid4().hex[:4]}__{safe_name}"
    os.makedirs(str(upload_dir), exist_ok=True)
    path = os.path.join(str(upload_dir), filename)
    try:
        with open(path, 'wb') as f:
            f.write(content)
    except OSError:
        return None

    ext = os.path.splitext(safe_name)[1].lower()
    attachment = {"id": uuid.uuid4().hex[:8], "name": safe_name, "size": len(content),
                  "kind": "binary", "path": path, "text": None, "lines": None,
                  "img_b64": None, "thumb_b64": None}
    if ext in _TEXT_EXTS and _printable_ratio(content) >= 0.6:
        text, lines = extract_text(path)
        attachment.update(kind="text", text=text, lines=lines)
    elif ext in _IMAGE_EXTS:
        attachment["img_b64"] = read_image_b64(path)
        attachment["thumb_b64"] = _make_thumb(path)
        attachment["kind"] = "image"
    return attachment


def humansize(size):
    for unit in ('B', 'KB', 'MB'):
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == 'B' else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def build_prompt(text, attachments):
    """Combine user text and attachment metadata into one agent prompt."""
    if not attachments:
        return text
    output = [text] if text else []
    output += ["", "---", "📎 已上传文件:"]
    for index, attachment in enumerate(attachments, 1):
        size = humansize(attachment["size"])
        if attachment["kind"] == "text" and attachment["text"] is not None:
            ext = os.path.splitext(attachment["name"])[1].lstrip('.')
            output += [
                f"{index}. {attachment['name']} (文本·{attachment['lines']}行) — 正文已注入 ↓",
                f"```{ext}", attachment["text"], "```",
            ]
        elif attachment["kind"] == "image":
            output.append(f"{index}. {attachment['name']} (图片·{size}) — 已作为图像附件发送")
        else:
            relative = os.path.relpath(attachment["path"], str(TEMP))
            tag = "文本" if attachment["kind"] == "text" else "二进制"
            large = (f"·{attachment['lines']}行大文件"
                     if attachment["kind"] == "text" and attachment["lines"] else "")
            output.append(
                f"{index}. {attachment['name']} ({tag}·{size}{large}) — "
                f"已落盘 {relative}(可用 file_read 读取)"
            )
    return "\n".join(output)
