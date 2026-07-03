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
        tool_repair._TELEMETRY_FILE.unlink(missing_ok=True)
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