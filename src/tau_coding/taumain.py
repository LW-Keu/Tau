import importlib
import importlib.util
import os, sys, threading, queue, time, json, re, random
from pathlib import Path

from tau_ai.keys import reload_taukeys
from tau_ai.clients import ToolClient, NativeToolClient, MixinSession, config_kind, resolve_client
from tau_ai.providers.openai import LLMSession, NativeOAISession
from tau_ai.providers.claude import ClaudeSession, NativeClaudeSession
from tau_agent.agent_loop import agent_runner_loop_events
from tau_agent.events import TurnStarted, render_event, event_to_json
from tau_agent.handler import TauHandler
from tau_agent.tools.utils import smart_format, get_global_memory, format_error, consume_file
from tau_paths import TAU_HOME, MEMORY, ASSETS, TEMP
from .runtime import initialize_runtime, language_suffix

def load_tool_schema(suffix=''):
    global TOOLS_SCHEMA
    TS = (ASSETS / f'tools_schema{suffix}.json').read_text(encoding='utf-8')
    TOOLS_SCHEMA = json.loads(TS if os.name == 'nt' else TS.replace('powershell', 'bash'))

def get_system_prompt():
    with open(str(ASSETS / f'prompts/sys_prompt{language_suffix()}.txt'), 'r', encoding='utf-8') as f: prompt = f.read()
    prompt += f"\nToday: {time.strftime('%Y-%m-%d %a')}\n"
    prompt += get_global_memory()
    return prompt


def _load_reflect(target, current=None):
    if os.path.isfile(target):
        spec = importlib.util.spec_from_file_location("reflect_script", target)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load reflect script: {target}")
        module = current or importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.reload(current) if current else importlib.import_module(target)
    source = getattr(module, "__file__", None)
    if not source:
        raise ImportError(f"Reflect target has no source file: {target}")
    return module, os.path.realpath(source)


class Tau:
    _slash_commands = {}

    @classmethod
    def register_slash_command(cls, name, handler):
        cls._slash_commands[name.lstrip('/')] = handler

    def __init__(self):
        initialize_runtime()
        load_tool_schema()
        os.makedirs(str(TEMP), exist_ok=True)
        self.lock = threading.Lock()
        self.task_dir = None
        self.history = []; self.handler = None;
        self.task_queue = queue.Queue()
        self.is_running = False; self.stop_sig = False; self.llm_no = 0;
        self.inc_out = False; self.verbose = True; self.show_mode = 'text'
        self.peer_hint = True
        self.log_path = str(TEMP / f'model_responses/model_responses_{int(time.time()*1e6)%1000000:06d}.txt')
        self.events_log_path = self.log_path.replace('.txt', '.events.jsonl')
        self.load_llm_sessions()

    def load_llm_sessions(self):
        taukeys, changed = reload_taukeys()
        if not changed and hasattr(self, 'llmclients'): return
        try: oldhistory = self.llmclient.backend.history
        except Exception: oldhistory = None
        llm_sessions = []
        for k, cfg in taukeys.items():
            try:
                kind = config_kind(k, cfg)
                if kind == 'mixin': llm_sessions += [{'mixin_cfg': cfg}]
                elif kind and (client := resolve_client(k, cfg)): llm_sessions += [client]
            except Exception as e: print(f'[WARN] skip LLM config {k}: {format_error(e)}')
        for i, s in enumerate(llm_sessions):
            if isinstance(s, dict) and 'mixin_cfg' in s:
                try:
                    mixin = MixinSession(llm_sessions, s['mixin_cfg'])
                    if isinstance(mixin._sessions[0], (NativeClaudeSession, NativeOAISession)): llm_sessions[i] = NativeToolClient(mixin)
                    else: llm_sessions[i] = ToolClient(mixin)
                except Exception as e: print(f'\n\n\n[ERROR] Failed to init MixinSession with cfg {s["mixin_cfg"]}: {e}!!!\n\n')
        if not llm_sessions: raise RuntimeError('No valid LLM config loaded from .tau/taukey.py — check api/config/cookie entries (run `tau configure`)')
        self.llmclients = llm_sessions
        self.llmclient = self.llmclients[self.llm_no%len(self.llmclients)]
        if oldhistory: self.llmclient.backend.history = oldhistory
    
    def next_llm(self, n=-1):
        self.load_llm_sessions()
        self.llm_no = ((self.llm_no + 1) if n < 0 else n) % len(self.llmclients)
        lastc = self.llmclient
        self.llmclient = self.llmclients[self.llm_no]
        try: self.llmclient.backend.history = lastc.backend.history
        except Exception: raise Exception('[ERROR] BAD Mixin config: Check your .tau/taukey.py (run `tau configure`)')
        self.llmclient.last_tools = ''
        name = self.get_llm_name(model=True)
        if 'glm' in name or 'minimax' in name or 'kimi' in name: load_tool_schema('_cn')
        else: load_tool_schema()
    def list_llms(self): 
        self.load_llm_sessions()
        return [(i, self.get_llm_name(b), i == self.llm_no) for i, b in enumerate(self.llmclients)]
    def get_llm_name(self, b=None, model=False):
        b = self.llmclient if b is None else b
        if isinstance(b, dict): return 'BADCONFIG_MIXIN'
        if model: return b.backend.model.lower()
        return f"{type(b.backend).__name__}/{b.backend.name}"

    def history_snapshot(self) -> str:
        """Serialized LLM history — consumed as the ``history`` var in
        do_code_run's inline_eval namespace (see tau_agent.handler)."""
        return json.dumps(self.llmclient.backend.history)

    def abort(self):
        if not self.is_running: return
        print('Abort current task...')
        self.stop_sig = True
        if self.handler is not None: self.handler.code_stop_signal.append(1)
            
    def put_task(self, query, source="user", images=None, events=None):
        display_queue = queue.Queue()
        self.task_queue.put({"query": query, "source": source, "images": images or [], "output": display_queue, "events": events})
        return display_queue

    # i know it is dangerous, but raw_query is dangerous enough it doesn't enlarge
    def _handle_slash_cmd(self, raw_query, event_queue):
        from tau_agent.events import RawText, TurnEnded
        if not raw_query.startswith('/'): return raw_query
        name = raw_query[1:].split(None, 1)[0]
        if handler := self._slash_commands.get(name):
            return handler(self, raw_query, event_queue)
        if _sm := re.match(r'/session\.(\w+)=(.*)', raw_query.strip()):
            k, v = _sm.group(1), _sm.group(2)
            vfile = str(TEMP / v)
            if os.path.isfile(vfile): v = Path(vfile).read_text(encoding='utf-8').strip()
            try: v = json.loads(v)  # cover number parsing
            except (json.JSONDecodeError, ValueError): pass
            setattr(self.llmclient.backend, k, v)
            event_queue.put(RawText(smart_format(f"✅ session.{k} = {repr(v)}", max_str_len=500)))
            event_queue.put(TurnEnded({"result": "SYSTEM_MESSAGE"}))
            return None
        if raw_query.strip() == '/resume':
            return r'帮我看看最近有哪些会话可以恢复。读model_responses/目录，按修改时间取最近10个文件，从每个文件里找最后一个<history>...</history>块，用一句话总结每个会话在聊什么，列表给我选。注意读文件后要把字面的\n替换成真换行才能正确匹配。'
        return raw_query

    def run(self, once: bool = False):
        while True:
            task = self.task_queue.get()
            raw_query, source, display_queue = task["query"], task["source"], task["output"]
            event_queue = task.get("events")
            if event_queue is None:
                event_queue = queue.Queue()
            raw_query = self._handle_slash_cmd(raw_query, event_queue)
            if raw_query is None:
                self.task_queue.task_done()
                if once: return
                continue
            self.is_running = True
            rquery = smart_format(raw_query.replace('\n', ' '), max_str_len=200)
            self.history.append(f"[USER]: {rquery}")
            
            sys_prompt = get_system_prompt() + getattr(self.llmclient.backend, 'extra_sys_prompt', '')
            if self.peer_hint: sys_prompt += f"\n[Peer] 用户提及其他会话/后台任务状态时: temp/model_responses/ (只找近期修改的文件尾部)\n"
            handler = TauHandler(self, self.history, str(TEMP))
            if self.handler and 'key_info' in self.handler.working: 
                ki = re.sub(r'\n\[SYSTEM\] 此为.*?工作记忆[。\n]*', '', self.handler.working['key_info'])  # 去旧
                handler.working['key_info'] = ki
                handler.working['passed_sessions'] = ps = self.handler.working.get('passed_sessions', 0) + 1
                if ps > 0: handler.working['key_info'] += f'\n[SYSTEM] 此为 {ps} 个对话前设置的key_info，若已在新任务，先更新或清除工作记忆。\n'
            self.handler = handler  # although new handler, the **full** history is in llmclient, so it is full history!
            self.llmclient.log_path = self.log_path
            events = agent_runner_loop_events(self.llmclient, sys_prompt, raw_query, handler, TOOLS_SCHEMA,
                                              max_turns=80, verbose=self.verbose)
            events_fh = None
            if self.events_log_path:
                try:
                    os.makedirs(os.path.dirname(self.events_log_path), exist_ok=True)
                    events_fh = open(self.events_log_path, 'a', encoding='utf-8', errors='replace')
                except Exception: events_fh = None
            try:
                full_resp = ""; last_pos = 0; curr_turn = 0; turn_resps = []
                for event in events:
                    if events_fh is not None:
                        try: events_fh.write(event_to_json(event) + '\n')
                        except Exception: pass
                    if event_queue is not None:
                        event_queue.put(event)
                    if consume_file(self.task_dir, '_stop'): self.abort()
                    if self.stop_sig: break
                    if isinstance(event, TurnStarted):
                        curr_turn = event.turn; turn_resps.append(''); continue
                    chunk = render_event(event, self.verbose)
                    full_resp += chunk;  turn_resps[-1] += chunk
                    if len(full_resp) - last_pos > 30 or isinstance(event, TurnStarted):
                        display_queue.put({'next': full_resp[last_pos:] if self.inc_out else full_resp,
                                           'source': source, 'turn': curr_turn, 'outputs': turn_resps[-2:]})
                        last_pos = len(full_resp)
                if self.inc_out and last_pos < len(full_resp): display_queue.put({'next': full_resp[last_pos:], 'source': source,
                                                                                  'turn': curr_turn, 'outputs': turn_resps[-2:]})
                display_queue.put({'done': full_resp, 'source': source, 'turn': curr_turn, 'outputs': turn_resps.copy()})
                self.history = handler.history_info
            except Exception as e:
                error = format_error(e)
                print(f"Backend Error: {error}")
                display_queue.put({'done': full_resp + f'\n```\n{error}\n```', 'error': error, 'source': source, 'turn': curr_turn, 'outputs': turn_resps.copy()})
            finally:
                if events_fh is not None:
                    try: events_fh.close()
                    except Exception: pass
                if self.stop_sig: print('User aborted the task.')
                self.is_running = self.stop_sig = False
                self.task_queue.task_done()
                if self.handler is not None: self.handler.code_stop_signal.append(1)
            if once: return

if __name__ == '__main__':
    import argparse
    from datetime import datetime
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', metavar='IODIR', help='一次性任务模式(文件IO)')
    parser.add_argument('--reflect', metavar='SCRIPT', help='反射模式：加载监控脚本，check()触发时发任务')
    parser.add_argument('--input', help='prompt')
    parser.add_argument('--llm_no', type=int, default=0)
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--nobg', action='store_true')
    args, _unknown = parser.parse_known_args()
    _reflect_args = dict(zip([k.lstrip('-') for k in _unknown[::2]], _unknown[1::2])) if _unknown else {}

    if args.task and not args.nobg:
        import subprocess, platform
        cmd = [sys.executable, "-m", "tau_coding.taumain"] + [
            arg for arg in sys.argv[1:] if arg != "--nobg"
        ] + ["--nobg"]
        d = str(TEMP / args.task); os.makedirs(d, exist_ok=True)
        p = subprocess.Popen(
            cmd,
            cwd=str(TAU_HOME),
            creationflags=0x08000000 if platform.system() == "Windows" else 0,
            stdout=open(os.path.join(d, "stdout.log"), "w", encoding="utf-8"),
            stderr=open(os.path.join(d, "stderr.log"), "w", encoding="utf-8"),
        )
        print(p.pid); sys.exit(0)

    agent = Tau()
    agent.next_llm(args.llm_no)
    agent.verbose = args.verbose
    threading.Thread(target=agent.run, daemon=True).start()

    if args.task:
        agent.peer_hint = False
        agent.task_dir = d = str(TEMP / args.task); nround = ''
        infile = os.path.join(d, 'input.txt')
        if args.input:
            os.makedirs(d, exist_ok=True)
            import glob; [os.remove(f) for f in glob.glob(os.path.join(d, 'output*.txt'))]
            with open(infile, 'w', encoding='utf-8') as f: f.write(args.input)
        if (fh := consume_file(d, '_history.json')): agent.llmclient.backend.history = json.loads(fh)
        with open(infile, encoding='utf-8') as f: raw = f.read()
        while True:
            dq = agent.put_task(raw, source='task')
            while 'done' not in (item := dq.get(timeout=300)): 
                if 'next' in item and random.random() < 0.95:  # 概率写一次中间结果
                    with open(f'{d}/output{nround}.txt', 'w', encoding='utf-8') as f: f.write(item.get('next', ''))
            with open(f'{d}/output{nround}.txt', 'w', encoding='utf-8') as f: f.write(item['done'] + '\n\n[ROUND END]\n')
            consume_file(d, '_stop')  # 已经成功停下来了，避免打断下次reply
            for _ in range(300):  # 等reply.txt，10分钟超时
                time.sleep(2)
                if (raw := consume_file(d, 'reply.txt')): break
            else: break
            nround = nround + 1 if isinstance(nround, int) else 1
    elif args.reflect:
        agent.peer_hint = False
        mod, reflect_path = _load_reflect(args.reflect)
        if hasattr(mod, 'init'): mod.init(_reflect_args)
        _mt = os.path.getmtime(reflect_path)
        print(f'[Reflect] loaded {args.reflect}' + (f' args={_reflect_args}' if _reflect_args else ''))
        while True:
            if os.path.getmtime(reflect_path) != _mt:
                try:
                    mod, reflect_path = _load_reflect(args.reflect, mod)
                    _mt = os.path.getmtime(reflect_path)
                    if hasattr(mod, 'init'): mod.init(_reflect_args)
                    print('[Reflect] reloaded')
                except Exception as e: print(f'[Reflect] reload error: {e}')
            time.sleep(getattr(mod, 'INTERVAL', 5))
            try: task = mod.check()
            except Exception as e: 
                print(f'[Reflect] check() error: {e}'); continue
            if task and task == '/exit': break
            if task is None: continue
            print(f'[Reflect] triggered: {task[:80]}')
            dq = agent.put_task(task, source='reflect')
            try:
                while 'done' not in (item := dq.get(timeout=180)): pass
                result = item['done']
                print(result)
            except Exception as e:
                if getattr(mod, 'ONCE', False): raise
                print(f'[Reflect] drain error: {e}'); result = f'[ERROR] {e}'
            log_dir = str(TEMP / 'reflect_logs'); os.makedirs(log_dir, exist_ok=True)
            script_name = os.path.splitext(os.path.basename(reflect_path))[0]
            open(os.path.join(log_dir, f'{script_name}_{datetime.now():%Y-%m-%d}.log'), 'a', encoding='utf-8').write(f'[{datetime.now():%m-%d %H:%M}]\n{result}\n\n')
            if (on_done := getattr(mod, 'on_done', None)):
                try: on_done(result)
                except Exception as e: print(f'[Reflect] on_done error: {e}')
            if getattr(mod, 'ONCE', False): print('[Reflect] ONCE=True, exiting.'); break
    else:
        try: import readline
        except Exception: pass
        agent.inc_out = True
        if sys.stdout.isatty():
            try: model = agent.get_llm_name(model=True) or '?'
            except Exception: model = '?'
            try:
                sys.stdout.write(f'\x1b[92m✦\x1b[0m \x1b[1mTau\x1b[0m '
                                 f'\x1b[90m· cli · model:\x1b[0m {model}\n')
                sys.stdout.flush()
            except Exception: pass
        while True:
            q = input('> ').strip()
            if not q: continue
            try:
                dq = agent.put_task(q, source='user')
                while True:
                    item = dq.get()
                    if 'next' in item: print(item['next'], end='', flush=True)
                    if 'done' in item: print(); break
            except KeyboardInterrupt:
                agent.abort()
                print('\n[Interrupted]')
