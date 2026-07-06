import json, re, os
from dataclasses import dataclass
from typing import Any, Optional
try: from plugins.hooks import trigger as _hook
except ImportError: _hook = lambda *a, **k: None
from .format import json_default, get_pretty_json, _clean_content, _compact_tool_args
from .tool_repair import repair_tool_input, safe_parse_args
@dataclass
class StepOutcome:
    data: Any
    next_prompt: Optional[str] = None
    should_exit: bool = False
def try_call_generator(func, *args, **kwargs):
    ret = func(*args, **kwargs)
    if hasattr(ret, '__iter__') and not isinstance(ret, (str, bytes, dict, list)): ret = yield from ret
    return ret

def _resolve_model(handler_self) -> str:
    """从 handler.parent.llmclient.model 取模型 id；失败返回空串。"""
    try:
        return getattr(getattr(getattr(handler_self, 'parent', None), 'llmclient', None), 'model', '') or ''
    except Exception:
        return ''

class BaseHandler:
    def turn_end_callback(self, response, tool_calls, tool_results, turn, next_prompt, exit_reason): return next_prompt
    def dispatch(self, tool_name, args, response, index=0, tool_num=1):
        method_name = f"do_{tool_name}"
        if hasattr(self, method_name):
            model = _resolve_model(self)
            schemas = getattr(self, 'TOOL_SCHEMAS', None)
            args, ok, notes = repair_tool_input(model, tool_name, args, schemas)
            if not ok:
                for n in notes:
                    yield n + "\n"
                return StepOutcome(None, next_prompt='；'.join(notes), should_exit=False)
            # 关系默认值产生的附注（"注意：..."）透明 yield；最后挂到 ret.data
            relational = []
            for n in notes:
                if n.startswith('注意'):
                    relational.append(n)
                else:
                    yield n + "\n"
            args['_index'] = index; args['_tool_num'] = tool_num
            _hook('tool_before', locals())
            ret = yield from try_call_generator(getattr(self, method_name), args, response)
            _hook('tool_after', locals())
            if relational and ret is not None and ret.data is not None:
                note_text = '\n\n'.join(relational)
                if isinstance(ret.data, dict):
                    ret.data.setdefault('note', note_text)
                elif isinstance(ret.data, str):
                    # str 路径(如 file_read 直接返回文件内容)不污染 data,
                    # 改走 next_prompt 通道,把附注作为追加 prompt 提示。
                    # 需 new StepOutcome 保留原 should_exit/data 行为。
                    ret = StepOutcome(ret.data, next_prompt=(ret.next_prompt or '') + '\n\n' + note_text, should_exit=ret.should_exit)
            return ret
        elif tool_name == 'bad_json':
            return StepOutcome(None, next_prompt=args.get('msg', 'bad_json'), should_exit=False)
        else:
            import difflib
            known = [m[3:] for m in dir(self) if m.startswith('do_')]
            hint = difflib.get_close_matches(tool_name, known, n=1)
            if hint:
                msg = f"未知工具 {tool_name}。你是想用 `{hint[0]}` 吗？可用工具：{', '.join(known)}"
            else:
                msg = f"未知工具 {tool_name}。可用工具：{', '.join(known)}"
            yield msg + "\n"
            return StepOutcome(None, next_prompt=msg, should_exit=False)

def exhaust(g):
    while True:
        try: next(g)
        except StopIteration as e: return e.value


def _render_tool_call(verbose, name, args):
    """生成工具调用的渲染字符串。verbose 时输出含参数详情的围栏块;否则输出紧凑单行。"""
    if verbose:
        return f"🛠️ Tool: `{name}`  📥 args:\n````text\n{get_pretty_json(args)}\n````\n"
    return f"🛠️ {name}({_compact_tool_args(name, args)})\n\n\n"


def _run_dispatch(gen, verbose):
    """统一处理 dispatch 生成器:verbose 时透传 yield 并加围栏, 否则静默耗尽。
    行为等价于原内嵌 proxy() + 围栏块。

    Empty `gen` short-circuits to `return e.value`, preserving dispatch()'s
    return value for callers like `bad_json` (which never yields).
    """
    try:
        first = next(gen)
    except StopIteration as e:
        return e.value
    def wrapped():
        yield first
        return (yield from gen)
    if not verbose:
        return exhaust(wrapped())
    yield '`````\n'
    outcome = yield from wrapped()
    yield '`````\n'
    return outcome


def agent_runner_loop(client, system_prompt, user_input, handler, tools_schema, 
                      max_turns=40, verbose=True, initial_user_content=None, yield_info=False):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_user_content if initial_user_content is not None else user_input}
    ]
    turn = 0;  handler.max_turns = max_turns
    _hook('agent_before', locals())
    while turn < handler.max_turns:
        turn += 1; turnstr = f'LLM Running (Turn {turn}) ...'
        if handler.parent.task_dir: turnstr = f'Turn {turn} ...'
        if verbose: turnstr = f'**{turnstr}**'
        if yield_info: yield {'turn': turn}
        yield f"\n\n{turnstr}\n\n"
        if turn%10 == 0: client.last_tools = ''  # 每10轮重置一次工具描述
        _hook('turn_before', locals())
        _hook('llm_before', locals())
        response_gen = client.chat(messages=messages, tools=tools_schema)
        if verbose:
            response = yield from response_gen
            yield '\n\n'
        else:
            response = exhaust(response_gen)
            cleaned = _clean_content(response.content)
            if cleaned: yield cleaned + '\n'
        _hook('llm_after', locals())

        tool_calls = []
        for tc in (response.tool_calls or []):
            args, err = safe_parse_args(tc.function.arguments)
            if args is None:
                tool_calls.append({'tool_name': 'bad_json', 'args': {
                    'msg': f'工具 {tc.function.name} 的参数不是合法 JSON（{err}）。'
                           f'请重新调用该工具，参数必须是一个 JSON 对象。'}, 'id': tc.id})
            else:
                tool_calls.append({'tool_name': tc.function.name, 'args': args, 'id': tc.id})
        if not tool_calls: tool_calls = [{'tool_name': 'no_tool', 'args': {}}]
       
        tool_results = []; next_prompts = set(); exit_reason = {}
        for ii, tc in enumerate(tool_calls):
            tool_name, args, tid = tc['tool_name'], tc['args'], tc.get('id', '')
            if tool_name == 'no_tool': pass
            else: yield _render_tool_call(verbose, tool_name, args)
            handler.current_turn = turn
            gen = handler.dispatch(tool_name, args, response, index=ii, tool_num=len(tool_calls))
            outcome = yield from _run_dispatch(gen, verbose)
            
            if outcome.should_exit: 
                exit_reason = {'result': 'EXITED', 'data': outcome.data}; break
            if not outcome.next_prompt: 
                exit_reason = {'result': 'CURRENT_TASK_DONE', 'data': outcome.data}; break
            if outcome.next_prompt.startswith('未知工具'): client.last_tools = ''
            if outcome.data is not None and tool_name != 'no_tool': 
                datastr = json.dumps(outcome.data, ensure_ascii=False, default=json_default) if type(outcome.data) in [dict, list] else str(outcome.data) 
                tool_results.append({'tool_use_id': tid, 'content': datastr})
            next_prompts.add(outcome.next_prompt)
        if len(next_prompts) == 0 or exit_reason:
            if len(handler._done_hooks) == 0 or exit_reason.get('result', '') == 'EXITED': break
            next_prompts.add(handler._done_hooks.pop(0))
        next_prompt = handler.turn_end_callback(response, tool_calls, tool_results, turn, '\n'.join(next_prompts), exit_reason)
        _hook('turn_after', locals())
        messages = [{"role": "user", "content": next_prompt, "tool_results": tool_results}]   # just new message, history is kept in *Session
    if exit_reason: handler.turn_end_callback(response, tool_calls, tool_results, turn, '', exit_reason)
    _hook('agent_after', locals())
    return exit_reason or {'result': 'MAX_TURNS_EXCEEDED'}
