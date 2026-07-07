"""Streamlit 上传功能纯逻辑(零 streamlit 依赖,可独立单测)。
负责:落盘 / 文本提取 / 图片编码 / prompt 组装。UI 在 app_v4.py。"""
import os
import time, uuid
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


def _printable_ratio(raw_bytes):
    """合法 UTF-8 且可打印字符占比。非 UTF-8 → 0.0(判定为二进制)。"""
    if not raw_bytes:
        return 1.0
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return 0.0
    printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
    return printable / max(len(text), 1)


def _make_thumb(path, max_size=400, quality=70):
    """best-effort 缩略图。无 PIL 返回 None。"""
    try:
        import io, base64
        from PIL import Image
        im = Image.open(path)
        im.thumbnail((max_size, max_size))
        if im.mode != 'RGB':
            im = im.convert('RGB')
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=quality)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception:
        return None


def save_upload(uf, upload_dir=UPLOAD_DIR):
    """校验大小 → 落盘(basename+时间戳+uuid)→ 按 ext+可打印率分流。
    返回附件元数据 dict;超大小上限或落盘失败返回 None。"""
    try:
        content = uf.getvalue()
    except Exception:
        return None
    if len(content) > MAX_FILE_SIZE:
        return None
    safe_name = os.path.basename(uf.name)  # 杜绝路径穿越
    ts = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    fname = f"{ts}__{uuid.uuid4().hex[:4]}__{safe_name}"
    os.makedirs(str(upload_dir), exist_ok=True)
    path = os.path.join(str(upload_dir), fname)
    try:
        with open(path, 'wb') as f:
            f.write(content)
    except OSError:
        return None

    ext = os.path.splitext(safe_name)[1].lower()
    att = {"id": uuid.uuid4().hex[:8], "name": safe_name, "size": len(content),
           "kind": "binary", "path": path,
           "text": None, "lines": None, "img_b64": None, "thumb_b64": None}
    if ext in _TEXT_EXTS and _printable_ratio(content) >= 0.6:
        text, lines = extract_text(path)
        att.update(kind="text", text=text, lines=lines)
    elif ext in _IMAGE_EXTS:
        att["img_b64"] = read_image_b64(path)
        att["thumb_b64"] = _make_thumb(path)  # 无 PIL → None,气泡回退 img_b64
        att["kind"] = "image"
    return att


def humansize(n):
    """字节数 → 人类可读。"""
    for unit in ('B', 'KB', 'MB'):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == 'B' else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def build_prompt(text, atts):
    """组装 query:用户文本 + 附件清单。文本类正文注入,binary 给路径,图片标注。"""
    if not atts:
        return text
    out = []
    if text:
        out.append(text)
    out += ["", "---", "📎 已上传文件:"]
    for i, a in enumerate(atts, 1):
        size = humansize(a["size"])
        if a["kind"] == "text" and a["text"] is not None:
            ext = os.path.splitext(a["name"])[1].lstrip('.')
            out += [f"{i}. {a['name']} (文本·{a['lines']}行) — 正文已注入 ↓",
                    f"```{ext}", a["text"], "```"]
        elif a["kind"] == "image":
            out.append(f"{i}. {a['name']} (图片·{size}) — 已作为图像附件发送")
        else:
            rel = os.path.relpath(a["path"], str(TEMP))
            tag = "文本" if a["kind"] == "text" else "二进制"
            big = f"·{a['lines']}行大文件" if (a["kind"] == "text" and a["lines"]) else ""
            out.append(f"{i}. {a['name']} ({tag}·{size}{big}) — 已落盘 {rel}(可用 file_read 读取)")
    return "\n".join(out)
