"""锁死 tool_repair 的注入路径：schema 来源不依赖 bootstrap/init_schemas。"""


def test_repair_injection_independent_of_global():
    """显式 schemas 参数优先；全局空时注入路径仍修复、不注入则静默 no-op。"""
    from core.agent import tool_repair
    from core.agent.handler import TauHandler

    tool_repair.SCHEMAS.clear()                      # 模拟"未 bootstrap"
    schemas = tool_repair.derive_schema(TauHandler)
    # 注入路径 → 修复生效（bare_value_wrap: 'A' -> ['A']）
    args, ok, _ = tool_repair.repair_tool_input(
        '', 'ask_user', {'question': 'q', 'candidates': 'A'}, schemas=schemas)
    assert ok and args['candidates'] == ['A']
    # 不注入且全局空 → 静默 no-op（schema 缺失，原样返回，不崩）
    args2, ok2, _ = tool_repair.repair_tool_input(
        '', 'ask_user', {'question': 'q', 'candidates': 'A'})
    assert ok2 and args2['candidates'] == 'A'        # 未被修复
