"""`/continue` command: list and restore past model response sessions."""
import ast, glob, json, os, re, time

from tau_agent.events import RawText, TurnEnded, TurnStarted, render_event, event_from_json

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'temp', 'model_responses')
_LOG_GLOB = os.path.join(_LOG_DIR, 'model_responses_*.txt')
_BLOCK_RE = re.compile(r'^=== (Prompt|Response) ===.*?\n(.*?)(?=^=== (?:Prompt|Response) ===|\Z)',
                       re.DOTALL | re.MULTILINE)
_SUMMARY_RE = re.compile(r'<summary>\s*(.*?)\s*</summary>', re.DOTALL)

def _rel_time(mtime):
    d = int(time.time() - mtime)
    if d < 60: return f'{d}秒前'
    if d < 3600: return f'{d // 60}分前'
    if d < 86400: return f'{d // 3600}小时前'
    return f'{d // 86400}天前'

def _pairs(content):
    blocks, pairs, pending = _BLOCK_RE.findall(content or ''), [], None
    for label, body in blocks:
        if label == 'Prompt': pending = body.strip()
        elif pending is not None:
            pairs.append((pending, body.strip())); pending = None
    return pairs

def _first_user(pairs):
    for p, _ in pairs:
        try: msg = json.loads(p)
        except Exception: continue
        if not isinstance(msg, dict): continue
        for blk in msg.get('content', []) or []:
            if isinstance(blk, dict) and blk.get('type') == 'text':
                t = (blk.get('text') or '').strip()
                if t and '<history>' not in t and not t.startswith('### [WORKING MEMORY]'):
                    return t
    for p, _ in pairs[:1]:
        for line in p.splitlines():
            s = line.strip()
            if s and not s.startswith('###'): return s
    return ''


def _last_summary(pairs):
    for _, response_body in reversed(pairs):
        try:
            blocks = ast.literal_eval(response_body)
        except Exception:
            continue
        if not isinstance(blocks, list):
            continue
        text_parts = []
        for block in blocks:
            if isinstance(block, dict) and block.get('type') == 'text':
                text = block.get('text', '')
                if isinstance(text, str) and text:
                    text_parts.append(text)
        match = _SUMMARY_RE.search('\n'.join(text_parts))
        if match:
            summary = match.group(1).strip()
            if summary:
                return summary
    return ''


def _preview_text(pairs):
    return _last_summary(pairs) or _first_user(pairs)

def _recent_context(my_pid, n=5):
    """扫描最近 n 个 model_response 文件（排除自身），提取 lastQ / lastA。"""
    out = []
    for f in sorted(glob.glob(_LOG_GLOB), key=os.path.getmtime, reverse=True):
        m = re.search(r'model_responses_(\d+)', os.path.basename(f))
        if not m or m.group(1) == str(my_pid): continue
        try: c = open(f, encoding='utf-8', errors='ignore').read()
        except Exception: continue
        q = s = ""
        for hm in re.finditer(r'<history>(.*?)</history>', c, re.DOTALL):
            u = re.search(r'\[USER\]:\s*(.+?)(?:\\n|<)', hm.group(1))
            if u: q = u.group(1)
        sm = _SUMMARY_RE.search(c)
        if sm: s = sm.group(1).strip()
        q, s = q[:60].strip(), s[:60].replace('\n', ' ').strip()
        out.append(f'· {m.group(1)} | lastQ: {q or "-"} | lastA: {s or "-"}')
        if len(out) >= n: break
    return ('[RecentContext] 近期并行会话（非当前）:\n' + '\n'.join(out) + '\n[/RecentContext]') if out else ""

def _parse_native_history(pairs):
    history = []
    for p, r in pairs:
        try: user_msg = json.loads(p)
        except Exception: return None
        try: blocks = ast.literal_eval(r)
        except Exception: return None
        if not (isinstance(user_msg, dict) and user_msg.get('role') == 'user'): return None
        if not isinstance(blocks, list): return None
        history.append(user_msg)
        history.append({'role': 'assistant', 'content': blocks})
    return history

def list_sessions(exclude_pid=None):
    """Newest-first list of (path, mtime, first_user_text, n_rounds)."""
    files = glob.glob(_LOG_GLOB)
    if exclude_pid is not None:
        tag = f'model_responses_{exclude_pid}.txt'
        files = [f for f in files if not f.endswith(tag)]
    out = []
    for f in files:
        try:
            with open(f, encoding='utf-8', errors='replace') as fh:
                content = fh.read()
        except Exception: continue
        pairs = _pairs(content)
        if not pairs: continue
        out.append((f, os.path.getmtime(f), _preview_text(pairs), len(pairs)))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
_MD_ESCAPE_RE = re.compile(r'([\\`*_\[\]])')
def _escape_md(s): return _MD_ESCAPE_RE.sub(r'\\\1', s)


def _agent_clients(agent):
    clients = []
    for client in getattr(agent, 'llmclients', []) or []:
        if client not in clients:
            clients.append(client)
    current = getattr(agent, 'llmclient', None)
    if current is not None and current not in clients:
        clients.insert(0, current)
    return clients


def _replace_backend_history(agent, history):
    backend = getattr(getattr(agent, 'llmclient', None), 'backend', None)
    if backend is not None and hasattr(backend, 'history'):
        backend.history = list(history or [])


def _current_log_path(pid=None):
    pid = os.getpid() if pid is None else pid
    return os.path.join(_LOG_DIR, f'model_responses_{pid}.txt')


def _snapshot_current_log(pid=None):
    """Persist current PID log as a standalone recoverable snapshot, then clear it."""
    path = _current_log_path(pid)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            content = fh.read()
    except Exception:
        return None
    if not _pairs(content):
        return None
    os.makedirs(_LOG_DIR, exist_ok=True)
    pid = os.getpid() if pid is None else pid
    stamp = time.strftime('%Y%m%d_%H%M%S')
    snapshot = os.path.join(_LOG_DIR, f'model_responses_snapshot_{pid}_{stamp}_{time.time_ns() % 1_000_000_000:09d}.txt')
    with open(snapshot, 'w', encoding='utf-8', errors='replace') as fh:
        fh.write(content)
    with open(path, 'w', encoding='utf-8', errors='replace'):
        pass
    return snapshot


def reset_conversation(agent, message='🆕 已开启新对话，当前上下文已清空'):
    """Abort current work and clear all known frontend-visible conversation state."""
    try:
        agent.abort()
    except Exception:
        pass
    _snapshot_current_log()
    if hasattr(agent, 'history'):
        agent.history = []
    for client in _agent_clients(agent):
        backend = getattr(client, 'backend', None)
        if backend is not None and hasattr(backend, 'history'):
            backend.history = []
        if hasattr(client, 'last_tools'):
            client.last_tools = ''
    if hasattr(agent, 'handler'):
        agent.handler = None
    return message

def format_list(sessions, limit=20):
    if not sessions: return '❌ 没有可恢复的历史会话'
    lines = ['**可恢复会话**（输入 `/continue N` 恢复第 N 个）：', '']
    for i, (_, mtime, first, n) in enumerate(sessions[:limit], 1):
        preview = _escape_md((first or '（无法预览）').replace('\n', ' ')[:60])
        lines.append(f'{i}. `{_rel_time(mtime)}` · **{n} 轮** · {preview}')
    return '\n'.join(lines)

def restore(agent, path):
    """Restore session at path. Returns (msg, is_full)."""
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            content = fh.read()
    except Exception as e: return f'❌ 读取失败: {e}', False
    pairs = _pairs(content)
    if not pairs: return f'❌ {os.path.basename(path)} 为空或格式不符', False
    history = _parse_native_history(pairs)
    name = os.path.basename(path)
    if history is not None:
        agent.abort()
        _replace_backend_history(agent, history)
        return f'✅ 已恢复 {len(pairs)} 轮完整对话（{name}）\n(已写入 backend.history，可直接继续)', True
    from .chatapp_common import _restore_native_history, _restore_text_pairs
    summary = _restore_text_pairs(content) or _restore_native_history(content)
    if not summary: return f'❌ {name} 无法解析（非 native 且无摘要可提取）', False
    agent.abort()
    agent.history.extend(summary)
    n = sum(1 for l in summary if l.startswith('[USER]: '))
    return f'⚠️ 非 native 格式，已降级恢复 {n} 轮摘要（{name}）\n(请输入新问题继续)', False

def handle(agent, query, event_queue):
    """Dispatch /continue or /continue N. Returns None if consumed else original query."""
    s = (query or '').strip()
    if s == '/continue':
        event_queue.put(RawText(format_list(list_sessions(exclude_pid=os.getpid()))))
        event_queue.put(TurnEnded({"result": "SYSTEM_MESSAGE"}))
        return None
    m = re.match(r'/continue\s+(\d+)\s*$', s)
    if m:
        sessions = list_sessions(exclude_pid=os.getpid())
        idx = int(m.group(1)) - 1
        if not (0 <= idx < len(sessions)):
            event_queue.put(RawText(f'❌ 索引越界（有效范围 1-{len(sessions)}）'))
            event_queue.put(TurnEnded({"result": "SYSTEM_MESSAGE"}))
            return None
        reset_conversation(agent, message=None)
        msg, _ = restore(agent, sessions[idx][0])
        event_queue.put(RawText(msg))
        event_queue.put(TurnEnded({"result": "SYSTEM_MESSAGE"}))
        return None
    return query


_INJECT_MARKERS = ('### [WORKING MEMORY]', '[SYSTEM TIPS]', '[SYSTEM]', '[System]',
                   '[DANGER]', '### [总结提炼经验]')


def _user_text(prompt_body):
    """User-typed text from a prompt JSON; '' if this is an agent auto-continuation.

    A Prompt is auto-continue when *either* (a) it carries any tool_result block
    (so it's the next round of an in-flight LLM call), or (b) its text blocks all
    match known injection prefixes ([WORKING MEMORY], [SYSTEM TIPS], [System]
    regenerate prompts, [DANGER] guards, etc.). Real first-prompts only contain
    one plain text block with no injection markers.
    """
    try: msg = json.loads(prompt_body)
    except Exception: return ''
    if not isinstance(msg, dict): return ''
    blocks = msg.get('content', []) or []
    if any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in blocks):
        return ''
    for blk in blocks:
        if isinstance(blk, dict) and blk.get('type') == 'text':
            t = (blk.get('text') or '').strip()
            if t and not any(mk in t for mk in _INJECT_MARKERS): return t
    return ''


def _assistant_text(response_body):
    """Joined plain text from a response blocks repr; '' on parse failure.
    Used by /export to grab the model's prose only, without tool noise.
    """
    try: blocks = ast.literal_eval(response_body)
    except Exception: return ''
    if not isinstance(blocks, list): return ''
    return '\n'.join(b['text'] for b in blocks
                     if isinstance(b, dict) and b.get('type') == 'text'
                     and isinstance(b.get('text'), str) and b['text'].strip())


def _events_log_path(txt_path: str) -> str:
    """Structured event log alongside the legacy Prompt/Response text log."""
    if txt_path.endswith('.txt'):
        return txt_path[:-4] + '.events.jsonl'
    return txt_path + '.events.jsonl'


def _read_events(path: str):
    """Yield typed events from a JSON Lines file."""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield event_from_json(line)
                except Exception:
                    continue
    except Exception:
        return


def _turns_from_events(events):
    """Group an event stream into per-turn event lists."""
    turns = []
    current = []
    for event in events:
        if isinstance(event, TurnStarted):
            if current:
                turns.append(current)
            current = [event]
        else:
            current.append(event)
    if current:
        turns.append(current)
    return turns


def extract_ui_messages(path):
    """Parse a model_responses log into [{role, content}, ...] for UI replay.

    User prompts are read from the legacy Prompt/Response text log (only the
    text log carries the original user message), while assistant/tool rendering
    is rebuilt from the structured `.events.jsonl` stream so it matches the
    live event renderer instead of a reverse-engineered string shape.
    """
    events_path = _events_log_path(path)
    if not os.path.exists(events_path):
        return []
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception:
        return []
    pairs = _pairs(content)
    if not pairs:
        return []
    turns = _turns_from_events(_read_events(events_path))
    # Guard against truncated/mismatched logs.
    n = min(len(pairs), len(turns))

    out, assistant = [], None
    for i in range(n):
        prompt, _ = pairs[i]
        user = _user_text(prompt)
        seg = ''.join(render_event(event, verbose=True) for event in turns[i])
        if user:
            if assistant is not None:
                out.append(assistant)
            out.append({'role': 'user', 'content': user})
            assistant = {'role': 'assistant', 'content': seg}
        else:
            if assistant is None:
                assistant = {'role': 'assistant', 'content': ''}
            assistant['content'] = (assistant['content'] or '') + seg
    if assistant is not None:
        out.append(assistant)
    return [m for m in out if (m.get('content') or '').strip()]


def handle_frontend_command(agent, query, exclude_pid=None):
    """Frontend-friendly /continue entry that returns text directly."""
    s = (query or '').strip()
    exclude_pid = os.getpid() if exclude_pid is None else exclude_pid
    if s == '/continue':
        return format_list(list_sessions(exclude_pid=exclude_pid))
    m = re.match(r'/continue\s+(\d+)\s*$', s)
    if not m:
        return '用法: /continue 或 /continue N'
    sessions = list_sessions(exclude_pid=exclude_pid)
    idx = int(m.group(1)) - 1
    if not (0 <= idx < len(sessions)):
        return f'❌ 索引越界（有效范围 1-{len(sessions)}）'
    reset_conversation(agent, message=None)
    msg, _ = restore(agent, sessions[idx][0])
    return msg


def install(cls):
    cls.register_slash_command('continue', handle)
