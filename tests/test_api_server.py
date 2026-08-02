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


class FakeTau:
    instances = []

    def __init__(self, text="final answer", error=None):
        self.text, self.error = text, error
        self.inc_out = False
        self.verbose = True
        self.aborted = False
        self.events = self.display = None
        self.__class__.instances.append(self)

    def put_task(self, prompt, source="user", images=None, events=None):
        self.prompt = prompt
        self.events = events
        self.display = queue.Queue()
        return self.display

    def run(self, once=False):
        self.events.put(RawText(self.text))
        item = {"done": self.text}
        if self.error:
            item["error"] = self.error
        else:
            self.events.put(TurnEnded({"result": "done"}))
        self.display.put(item)

    def abort(self):
        self.aborted = True


def test_non_streaming_completion_uses_fresh_tau_and_standard_envelope():
    FakeTau.instances.clear()
    client = TestClient(create_app("secret", tau_factory=FakeTau))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent",
        "messages": [{"role": "user", "content": "hello"}],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "tau-agent"
    assert body["choices"][0]["message"] == {
        "role": "assistant", "content": "final answer",
    }
    assert body["choices"][0]["finish_reason"] == "stop"
    assert FakeTau.instances[0].prompt == "hello"


def test_non_streaming_runtime_failure_is_openai_error():
    client = TestClient(create_app(
        "secret", tau_factory=lambda: FakeTau(error="backend exploded"),
    ))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent",
        "messages": [{"role": "user", "content": "hello"}],
    })
    assert response.status_code == 500
    assert response.json()["error"]["message"] == "backend exploded"


class ExplodingTau(FakeTau):
    def run(self, once=False):
        raise RuntimeError("runner exploded")


def test_non_streaming_runner_failure_is_openai_error():
    client = TestClient(create_app("secret", tau_factory=ExplodingTau))
    response = []
    request = threading.Thread(
        target=lambda: response.append(client.post(
            "/v1/chat/completions", headers=_headers(), json={
                "model": "tau-agent",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )),
        daemon=True,
    )
    request.start()
    request.join(timeout=1)
    assert not request.is_alive()
    assert response[0].status_code == 500
    assert response[0].json()["error"] == {
        "message": "runner exploded", "type": "server_error",
        "code": "tau_run_failed",
    }


def test_tau_initialization_failure_is_openai_error():
    def fail_init():
        raise RuntimeError("invalid Tau config")

    client = TestClient(create_app("secret", tau_factory=fail_init))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent",
        "messages": [{"role": "user", "content": "hello"}],
    })
    assert response.status_code == 500
    assert response.json()["error"] == {
        "message": "invalid Tau config", "type": "server_error",
        "code": "tau_init_failed",
    }
