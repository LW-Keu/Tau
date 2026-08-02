import queue
import threading

import pytest
from fastapi.testclient import TestClient

from apps.api.server import APIError, build_prompt, create_app, parse_chat
import tau_coding.taumain as taumain
from tau_agent.events import RawText, TurnEnded, TurnStarted


class _Backend:
    extra_sys_prompt = ""
    history = []


class _Client:
    backend = _Backend()
    log_path = None


class _Handler:
    working = {}
    history_info = []
    code_stop_signal = []


def _bare_tau():
    taumain.TOOLS_SCHEMA = []
    agent = taumain.Tau.__new__(taumain.Tau)
    agent.task_queue = queue.Queue()
    agent.task_dir = None
    agent.history = []
    agent.handler = None
    agent.llmclient = _Client()
    agent.peer_hint = False
    agent.verbose = True
    agent.inc_out = True
    agent.is_running = False
    agent.stop_sig = False
    agent.log_path = ""
    agent.events_log_path = ""
    return agent


def _done(output):
    while True:
        item = output.get_nowait()
        if "done" in item: return item


def test_tau_run_once_exits_after_one_task(monkeypatch):
    agent = _bare_tau()
    monkeypatch.setattr(taumain, "get_system_prompt", lambda: "system")
    monkeypatch.setattr(taumain, "TauHandler", lambda *args: _Handler())
    monkeypatch.setattr(
        taumain,
        "agent_runner_loop_events",
        lambda *args, **kwargs: iter((
            TurnStarted(1), RawText("answer"), TurnEnded({"result": "done"}),
        )),
    )
    output = agent.put_task("hello")
    worker = threading.Thread(target=agent.run, kwargs={"once": True})
    worker.start()
    worker.join(timeout=1)
    assert not worker.is_alive()
    assert _done(output)["done"] == "answer"
    assert agent.task_queue.unfinished_tasks == 0


def test_tau_done_item_exposes_backend_error(monkeypatch):
    agent = _bare_tau()
    monkeypatch.setattr(taumain, "get_system_prompt", lambda: "system")
    monkeypatch.setattr(taumain, "TauHandler", lambda *args: _Handler())

    def fail(*args, **kwargs):
        yield TurnStarted(1)
        raise RuntimeError("backend exploded")

    monkeypatch.setattr(taumain, "agent_runner_loop_events", fail)
    output = agent.put_task("hello")
    agent.run(once=True)
    done = _done(output)
    assert "backend exploded" in done["error"]
    assert "backend exploded" in done["done"]


def _headers(key="secret"):
    return {"Authorization": f"Bearer {key}"}


def test_health_is_public_and_models_require_bearer_auth():
    client = TestClient(create_app("secret", tau_factory=lambda: None))
    assert client.get("/health").json() == {"status": "ok"}
    denied = client.get("/v1/models")
    assert denied.status_code == 401
    assert denied.json()["error"]["type"] == "authentication_error"
    models = client.get("/v1/models", headers=_headers()).json()
    assert models["object"] == "list"
    assert [item["id"] for item in models["data"]] == ["tau-agent"]


def test_parse_chat_accepts_text_and_ignores_sampling_controls():
    chat = parse_chat({
        "model": "tau-agent",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": True,
        "temperature": 0.2,
        "tools": [{"type": "function"}],
    })
    assert chat.stream is True
    assert chat.messages[-1].content == "hello"


def test_parse_chat_rejects_multimodal_content():
    try:
        parse_chat({
            "model": "tau-agent",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "hello"},
            ]}],
        })
    except APIError as error:
        assert error.status == 400
        assert error.code == "unsupported_content"
    else:
        raise AssertionError("multimodal content was accepted")


@pytest.mark.parametrize(("payload", "code"), [
    ({"model": "other", "messages": [
        {"role": "user", "content": "hello"},
    ]}, "model_not_found"),
    ({"model": "tau-agent", "messages": [
        {"role": "tool", "content": "output"},
    ]}, "unsupported_role"),
    ({"model": "tau-agent", "messages": [
        {"role": "assistant", "content": "not a user request"},
    ]}, "invalid_messages"),
])
def test_parse_chat_rejects_incompatible_requests(payload, code):
    with pytest.raises(APIError) as raised:
        parse_chat(payload)
    assert raised.value.code == code


def test_build_prompt_labels_prior_workbuddy_history():
    chat = parse_chat({
        "model": "tau-agent",
        "messages": [
            {"role": "system", "content": "be concise"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "continue"},
        ],
    })
    prompt = build_prompt(chat)
    assert "[SYSTEM]\nbe concise" in prompt
    assert "[USER]\nfirst" in prompt
    assert "[ASSISTANT]\nreply" in prompt
    assert prompt.endswith("Current user request:\ncontinue")
