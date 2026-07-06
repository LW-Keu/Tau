"""tool_repair 单元测试 — 守护两大陷阱（opaque 不误伤 + 修复顺序）不回归。"""
import pytest


@pytest.fixture(autouse=True)
def _reset_schemas_and_stats():
    """每个用例独立，互不污染 SCHEMAS / REPAIR_STATS / jsonl。"""
    from core.agent import tool_repair
    from core.agent.handler import TauHandler
    tool_repair.init_schemas(TauHandler)
    tool_repair.REPAIR_STATS.clear()
    # 清掉落盘
    try:
        tool_repair._get_telemetry_file().unlink(missing_ok=True)
    except Exception:
        pass
    yield
    tool_repair.REPAIR_STATS.clear()


def _repair(model, tool, args):
    from core.agent.tool_repair import repair_tool_input
    return repair_tool_input(model, tool, args)


# ---- 1: safe_parse_args 正常 ----
def test_safe_parse_args_ok():
    from core.agent.tool_repair import safe_parse_args
    args, err = safe_parse_args('{"a": 1}')
    assert args == {"a": 1} and err is None


# ---- 2: safe_parse_args 宽松与失败 ----
def test_safe_parse_args_lenient():
    from core.agent.tool_repair import safe_parse_args
    args, err = safe_parse_args('{"a":1,}')
    assert args == {"a": 1} and err == 'lenient_json'
    args2, err2 = safe_parse_args('not json at all')
    assert args2 is None and err2 is not None


# ---- 3: opaque content 不被解析为数组 ----
def test_opaque_content_preserved():
    args, ok, notes = _repair('', 'file_write', {'path': 'a.txt', 'content': '["a","b"]'})
    assert ok is True
    assert args['content'] == '["a","b"]', "opaque 字段 content 绝不能被当 JSON 解析"


# ---- 4: stringified_array 优先于 bare_value_wrap ----
def test_stringified_array_before_wrap():
    args, ok, notes = _repair('', 'ask_user', {'question': 'q', 'candidates': '["A","B"]'})
    assert ok is True
    assert args['candidates'] == ['A', 'B'], f"应为两元素列表，实得 {args.get('candidates')}"


# ---- 5: 裸值包装为单元素列表 ----
def test_bare_value_wrap():
    args, ok, notes = _repair('', 'ask_user', {'question': 'q', 'candidates': 'A'})
    assert ok is True
    assert args['candidates'] == ['A']


# ---- 6: null optional 字段被剔除 ----
def test_null_optional_dropped():
    """start/count 在 file_read schema 里非 required，传 None 应被剔除。"""
    args, ok, notes = _repair('', 'file_read', {'path': 'a', 'start': None})
    assert ok is True
    assert 'start' not in args


# ---- 7: 空对象 {} → [] ----
def test_empty_object_placeholder():
    args, ok, notes = _repair('', 'ask_user', {'question': 'q', 'candidates': {}})
    assert ok is True
    assert args['candidates'] == []


# ---- 8: 布尔字符串 truthy 反转修复 ----
def test_coerce_bool():
    args, ok, notes = _repair('', 'web_scan', {'tabs_only': 'false'})
    assert ok is True
    assert args['tabs_only'] is False, "字符串 'false' 应被强转为布尔 False"


# ---- 9: md_link_leak 兜底 ----
def test_md_link_leak():
    args1, ok1, _ = _repair('', 'file_read', {'path': '[a.txt](a.txt)'})
    assert ok1 is True and args1['path'] == 'a.txt'
    args2, ok2, _ = _repair('', 'file_read', {'path': '[doc](https://x.com/y)'})
    assert ok2 is True and args2['path'] == '[doc](https://x.com/y)', "真链接不动"


# ---- 10: 关系默认值 + 附注以"注意"开头 ----
def test_relational_defaults_file_read():
    args, ok, notes = _repair('', 'file_read', {'path': 'a.txt', 'count': 50})
    assert ok is True
    assert args['start'] == 1
    assert any(n.startswith('注意') for n in notes), f"附注应为中性'注意'提示，实得 {notes}"
    assert not any('[Error]' in n for n in notes), "附注不能带 [Error] 前缀"


# ---- 11: 快路径零拷贝 ----
def test_fast_path_zero_copy():
    raw = {'path': 'a.txt', 'start': 1, 'count': 100}
    args, ok, notes = _repair('', 'file_read', raw)
    assert ok is True
    assert args is raw, f"合法输入应原样返回，未拷贝；实得 args={args} raw={raw}"


# ---- 12: 别名 falsy 值（0 不被 or 吞掉） ----
def test_alias_falsy_value():
    args, ok, notes = _repair('', 'web_execute_js', {'script': 'alert(0)', 'tab_id': 0})
    assert ok is True
    assert args.get('switch_tab_id') == 0, f"tab_id=0 应被归一为 switch_tab_id=0；实得 {args}"
    assert 'tab_id' not in args


# ---- 13 (M-8 推荐): no-type 字段的契约锁定 ----
def test_no_type_constraint_passthrough():
    """switch_tab_id 默认值是 None，AST 推导无 type；validate 当 any 处理。

    锁定：当 AST 推导产生 `{}` spec（无 type），字段接受任何**非 None** 值，
    shape_fix 不试图强转（因 expected 为 None 时跳过）。
    覆盖 controller-approved 的 `stype is None` 与 `expected is None` 两处偏离。
    """
    # 1) 字符串 session ID 通过（string 不是 None，validate 不报 issue）
    args, ok, _ = _repair('', 'web_scan', {'switch_tab_id': 'session-abc-123'})
    assert ok is True
    assert args['switch_tab_id'] == 'session-abc-123'

    # 2) None 不通过 validate（no-type spec 仍把 None 视为 null 不合法）
    #    形状修复跳过（expected is None），返回 ok=False 含可读 note
    args2, ok2, notes = _repair('', 'web_scan', {'switch_tab_id': None})
    assert ok2 is False
    assert any('switch_tab_id' in n for n in notes), f"note 应指向字段，实得 {notes}"
    assert not any('[Error]' in n for n in notes)

    # 3) 整数通过（运行时类型为 int 时也兼容）
    args3, ok3, _ = _repair('', 'web_scan', {'switch_tab_id': 0})
    assert ok3 is True and args3['switch_tab_id'] == 0

    # 4) Unicode 字符串通过
    args4, ok4, _ = _repair('', 'web_scan', {'switch_tab_id': '会话-unicode-é'})
    assert ok4 is True and args4['switch_tab_id'] == '会话-unicode-é'

# ============================================================================
# /review Step 5.8e: 测试 gap 补齐 (testing specialist T1-T6)
# ============================================================================

# ---- T1: opaque 8 字段全覆盖(原仅 content) ----
@pytest.mark.parametrize("field,tool", [
    ("content", "file_write"),
    ("old_content", "file_patch"),
    ("new_content", "file_patch"),
    ("code", "code_run"),
    ("script", "web_execute_js"),
    ("question", "ask_user"),
    ("key_info", "update_working_checkpoint"),
])
def test_opaque_field_preserved_parametrized(field, tool):
    """所有 opaque-hint 字段绝不能把 '["a","b"]' 解析为 list。"""
    args, ok, _ = _repair('', tool, {field: '["a","b"]'})
    assert ok, f"{tool}.{field} 应通过(ok=True)"
    assert args[field] == '["a","b"]', f"{tool}.{field} 应保持字符串原样"


# ---- T2: safe_parse_args 边界(markdown-fenced / None / empty) ----
def test_safe_parse_args_markdown_fenced():
    from core.agent.tool_repair import safe_parse_args
    args, err = safe_parse_args('```json\n{"a": 1}\n```')
    assert args == {"a": 1} and err == 'lenient_json'


def test_safe_parse_args_empty_and_none():
    from core.agent.tool_repair import safe_parse_args
    a1, e1 = safe_parse_args("")
    assert a1 is None and e1 is not None
    a2, e2 = safe_parse_args(None)
    assert a2 is None and e2 is not None, "None 输入应被 (raw or '').strip() 兜底"


# ---- T3: repair_tool_input non-dict passthrough ----
@pytest.mark.parametrize("bad_input", [None, ["a", "b"], "string-not-dict", 42])
def test_repair_passthrough_on_non_dict(bad_input):
    out, ok, notes = _repair('', 'ask_user', bad_input)
    assert out is bad_input
    assert ok is True
    assert notes == []


# ---- T4: _fix_coerce_int 边界(负数 / fraction / inf / 不可修复) ----
@pytest.mark.parametrize("raw_value,expected", [
    ("42", 42),
    ("-1", -1),
    ("1.5", 1),     # 截断
    ("-3.9", -3),   # 负分数截断
])
def test_coerce_int_valid(raw_value, expected):
    args, ok, _ = _repair('', 'file_read', {'path': 'a', 'start': raw_value})
    assert ok and args['start'] == expected


def test_coerce_int_unfixable_keeps_input_or_rejects():
    # 'not-a-number' → int(float(x)) raises ValueError → shape_fix 跳过 → validate 仍 fail
    args, ok, notes = _repair('', 'file_read', {'path': 'a', 'start': 'not-a-number'})
    assert (ok is False) or (isinstance(args.get('start'), str)), \
        f"不可修复的整数应 ok=False 或保留原值；实得 ok={ok} args={args}"


# ---- T5: apply_relational_defaults 边界 ----
def test_relational_defaults_both_provided_no_note():
    args, ok, notes = _repair('', 'file_read', {'path': 'a', 'start': 5, 'count': 10})
    assert ok
    assert notes == [], f"两字段都给就不该有附注；实得 {notes}"
    assert args['start'] == 5 and args['count'] == 10


def test_relational_defaults_neither_provided():
    args, ok, notes = _repair('', 'file_read', {'path': 'a'})
    assert ok
    # 无 start 也无 count → apply_relational_defaults 不触发(两条分支都需 start XOR count)
    assert 'start' not in args
    assert 'count' not in args


def test_relational_defaults_file_patch_missing_old_content():
    """file_patch 缺 old_content 应触发附注(P1 #3 扩展)。"""
    args, ok, notes = _repair('', 'file_patch', {'path': 'a', 'new_content': 'x'})
    assert ok
    assert any('old_content' in n for n in notes), f"应提示 old_content 缺失；实得 {notes}"


def test_relational_defaults_file_write_bad_mode():
    """file_write 非标准 mode 值应触发附注(P1 #3 扩展)。"""
    args, ok, notes = _repair('', 'file_write', {'path': 'a', 'content': 'x', 'mode': 'evil'})
    assert ok
    assert any('mode' in n for n in notes), f"应警告 mode 非标准值；实得 {notes}"


# ---- T6: ok=False 含可读 note 的失败路径 ----
def test_repair_unfixable_type_returns_ok_false_with_note():
    # tabs_only schema 是 boolean;传入嵌套 dict 不可修复
    args, ok, notes = _repair('', 'web_scan', {'tabs_only': {'nested': 'dict'}})
    assert ok is False
    assert any('tabs_only' in n for n in notes), f"note 应指向字段；实得 {notes}"
    assert any('请修正' in n or '重试' in n for n in notes), f"应含重试提示；实得 {notes}"
    assert not any('[Error]' in n for n in notes), "note 不能带 [Error] 前缀"
