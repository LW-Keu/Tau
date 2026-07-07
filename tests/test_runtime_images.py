"""runtime images 多模态补线测试。"""


def test_build_initial_content_no_images():
    from core.agent.runtime import _build_initial_user_content
    # images 为空 → None(向后兼容,loop 用 user_input 作 content)
    assert _build_initial_user_content("hello", []) is None
    assert _build_initial_user_content("hello", None) is None


def test_build_initial_content_with_images():
    from core.agent.runtime import _build_initial_user_content
    result = _build_initial_user_content("看这张图", ["data:image/png;base64,AAA"])
    assert isinstance(result, list)
    assert len(result) == 2
    # 首个 part 是文本
    assert result[0] == {"type": "text", "text": "看这张图"}


def test_build_initial_content_url_format():
    from core.agent.runtime import _build_initial_user_content
    uri = "data:image/png;base64,AAA"
    result = _build_initial_user_content("hi", [uri])
    # image_url part 结构 = OpenAI 风格,messages.py 已认
    assert result[1] == {"type": "image_url", "image_url": {"url": uri}}


def test_build_initial_content_multiple_images():
    from core.agent.runtime import _build_initial_user_content
    result = _build_initial_user_content("hi", ["data:image/png;base64,A", "data:image/jpeg;base64,B"])
    assert len(result) == 3  # 1 text + 2 image


def test_runtime_unpacks_images():
    """run() 必须解包 task['images'] 并传 initial_user_content —— 防回归成死参数。"""
    import inspect
    from core.agent import runtime
    src = inspect.getsource(runtime.Tau.run)
    # 解包 images(任一写法皆可)
    assert ('task["images"]' in src) or ('task.get("images"' in src)
    # 调用 _build_initial_user_content 并传给 loop
    assert '_build_initial_user_content' in src
    assert 'initial_user_content' in src
