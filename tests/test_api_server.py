import asyncio
import json
import queue
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from apps.api import server
from apps.api.server import APIError, build_prompt, create_app, parse_chat
import tau_coding.taumain as taumain
import tau_coding.cli as tau_cli
from tau_agent.events import (
    RawText, ToolCallStart, ToolOutputChunk, ToolOutputEnd, ToolOutputStart,
    TurnEnded, TurnStarted,
)
from tau_coding.commands._launchers import LAUNCHERS


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


def test_api_launcher_is_registered():
    assert LAUNCHERS["api"]["cmd"] == ["python", "{APPS}/api/server.py"]


def test_main_refuses_to_start_without_api_key(monkeypatch):
    monkeypatch.delenv("TAU_API_KEY", raising=False)
    with pytest.raises(SystemExit) as raised:
        server.main([])
    assert raised.value.code == 2


def test_main_binds_loopback_and_accepts_port_override(monkeypatch):
    called = {}
    monkeypatch.setenv("TAU_API_KEY", "secret")
    monkeypatch.setattr(
        server.uvicorn, "run", lambda app, **kwargs: called.update(kwargs),
    )
    server.main(["--port", "9001"])
    assert called == {"host": "127.0.0.1", "port": 9001}


def test_tau_cli_preserves_api_launcher_argument_order(monkeypatch):
    called = {}
    monkeypatch.setattr(sys, "argv", ["tau", "api", "--port", "9001"])
    monkeypatch.setattr(tau_cli, "require_assets", lambda: None)
    monkeypatch.setattr(
        tau_cli._launchers_mod, "run",
        lambda name, args: called.update(name=name, args=args),
    )
    tau_cli.main()
    assert called == {"name": "api", "args": ["--port", "9001"]}


def test_tau_cli_keeps_version_as_a_global_option_after_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tau", "api", "--version"])
    monkeypatch.setattr(
        tau_cli._launchers_mod,
        "run",
        lambda *_args: pytest.fail("global --version must not launch a frontend"),
    )
    tau_cli.main()
    assert capsys.readouterr().out == "Tau v0.1.0\n"


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
        self.source = source
        self.events = events
        self.display = queue.Queue()
        return self.display

    def run(self, once=False):
        self.once = once
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
    assert FakeTau.instances[0].source == "api"
    assert FakeTau.instances[0].once is True


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


def _sse_payloads(text):
    return [line[6:] for line in text.splitlines() if line.startswith("data: ")]


def test_streaming_completion_emits_role_progress_terminal_and_done():
    FakeTau.instances.clear()
    client = TestClient(create_app("secret", tau_factory=FakeTau))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    payloads = _sse_payloads(response.text)
    chunks = [json.loads(value) for value in payloads[:-1]]
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert chunks[0]["choices"][0]["delta"] == {"role": "assistant"}
    content = "".join(
        item["choices"][0]["delta"].get("content", "")
        for item in chunks if "choices" in item
    )
    assert content == "final answer"
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    assert payloads[-1] == "[DONE]"
    assert FakeTau.instances[0].aborted is False


class PartialEventTau(FakeTau):
    def __init__(self, text="final"):
        super().__init__(text=text)

    def run(self, once=False):
        self.once = once
        self.events.put(RawText(self.text))
        self.display.put({"done": "final answer"})


@pytest.mark.parametrize(("tau_factory", "expected"), [
    (PartialEventTau, "final answer"),
    (lambda: PartialEventTau(text="progress"), "progressfinal answer"),
])
def test_streaming_completion_reconciles_authoritative_display_text(
    tau_factory, expected,
):
    client = TestClient(create_app("secret", tau_factory=tau_factory))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    chunks = [json.loads(value) for value in _sse_payloads(response.text)[:-1]]
    content = "".join(
        item["choices"][0]["delta"].get("content", "")
        for item in chunks if "choices" in item
    )
    assert content == expected


class ToolProgressTau(FakeTau):
    def run(self, once=False):
        self.once = once
        self.events.put(ToolCallStart("shell", {"cmd": "pwd"}))
        self.events.put(ToolOutputStart())
        self.events.put(ToolOutputChunk("workspace"))
        self.events.put(ToolOutputEnd())
        self.events.put(TurnEnded({"result": "done"}))
        self.display.put({"done": ""})


def test_streaming_completion_renders_typed_tool_progress():
    client = TestClient(create_app("secret", tau_factory=ToolProgressTau))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    chunks = [json.loads(value) for value in _sse_payloads(response.text)[:-1]]
    content = "".join(
        item["choices"][0]["delta"].get("content", "")
        for item in chunks if "choices" in item
    )
    assert "Tool: `shell`" in content
    assert "workspace" in content


def test_streaming_runtime_failure_uses_error_frame_then_done():
    agent = FakeTau(error="backend exploded")
    client = TestClient(create_app("secret", tau_factory=lambda: agent))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    payloads = _sse_payloads(response.text)
    assert json.loads(payloads[-2])["error"] == {
        "message": "backend exploded", "type": "server_error",
        "code": "tau_run_failed",
    }
    assert payloads[-1] == "[DONE]"
    assert agent.aborted is False


def test_streaming_runner_failure_uses_error_frame_then_done():
    client = TestClient(create_app("secret", tau_factory=ExplodingTau))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    payloads = _sse_payloads(response.text)
    assert json.loads(payloads[-2])["error"]["message"] == "runner exploded"
    assert payloads[-1] == "[DONE]"


def test_concurrent_requests_create_isolated_tau_instances():
    FakeTau.instances.clear()
    app = create_app("secret", tau_factory=FakeTau)
    body = {"model": "tau-agent", "messages": [
        {"role": "user", "content": "hello"},
    ]}

    def post(_):
        with TestClient(app) as client:
            return client.post(
                "/v1/chat/completions", headers=_headers(), json=body,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(post, range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert len(FakeTau.instances) == 2
    assert FakeTau.instances[0] is not FakeTau.instances[1]
    assert FakeTau.instances[0].events is not FakeTau.instances[1].events
    assert [instance.source for instance in FakeTau.instances] == ["api", "api"]
    assert [instance.once for instance in FakeTau.instances] == [True, True]


def test_abort_is_request_local():
    from apps.api.server import TauExecution

    first, second = FakeTau(), FakeTau()
    run_one = TauExecution(lambda: first, "one")
    run_two = TauExecution(lambda: second, "two")
    run_one.abort()
    assert first.aborted is True
    assert second.aborted is False
    assert run_two.wait().text == "final answer"


def test_stream_disconnect_aborts_only_its_execution():
    from apps.api.server import TauExecution, stream_completion

    class DisconnectedRequest:
        async def is_disconnected(self):
            return True

    first, second = FakeTau(), FakeTau()
    run_one = TauExecution(lambda: first, "one")
    run_two = TauExecution(lambda: second, "two")

    async def consume_disconnected_stream():
        return [frame async for frame in stream_completion(
            DisconnectedRequest(), run_one,
        )]

    frames = asyncio.run(consume_disconnected_stream())
    assert len(frames) == 1
    assert first.aborted is True
    assert second.aborted is False
    assert run_two.wait().text == "final answer"


class SilentTau(FakeTau):
    def run(self, once=False):
        self.once = once


def test_runner_completion_without_display_done_does_not_hang():
    from apps.api.server import TauExecution

    execution = TauExecution(SilentTau, "hello")
    result = []
    waiter = threading.Thread(
        target=lambda: result.append(execution.wait()), daemon=True,
    )
    waiter.start()
    waiter.join(timeout=1)
    assert not waiter.is_alive()
    assert result[0].text == ""
    assert result[0].error == "Tau runner exited without a terminal result"


class DuplicateDoneTau(FakeTau):
    def run(self, once=False):
        super().run(once=once)
        self.display.put({"done": "duplicate"})


def test_duplicate_display_done_emits_one_stream_terminal():
    client = TestClient(create_app("secret", tau_factory=DuplicateDoneTau))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    payloads = _sse_payloads(response.text)
    chunks = [json.loads(value) for value in payloads[:-1]]
    assert sum(
        chunk["choices"][0]["finish_reason"] == "stop"
        for chunk in chunks if "choices" in chunk
    ) == 1
    assert payloads.count("[DONE]") == 1


class LateEventTau(FakeTau):
    def __init__(self):
        super().__init__()
        self.release_tail = threading.Event()

    def run(self, once=False):
        self.once = once
        self.display.put({"done": "final answer"})
        self.release_tail.wait(timeout=1)
        self.events.put(RawText("tail"))


def test_event_pump_drains_events_emitted_as_runner_finishes():
    from apps.api.server import TauExecution

    agent = LateEventTau()
    execution = TauExecution(lambda: agent, "hello")
    threading.Timer(0.1, agent.release_tail.set).start()
    events = []
    while not events or events[-1].kind != "done":
        event = execution.next_event(timeout=2)
        assert event is not None
        events.append(event)
    assert [(event.kind, event.text) for event in events] == [
        ("delta", "tail"), ("done", "final answer"),
    ]


class DisplayRaceQueue(queue.Queue):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    def get_nowait(self):
        try:
            return super().get_nowait()
        except queue.Empty:
            if not self.agent.display_checked.is_set():
                self.agent.worker_ready.wait(timeout=1)
                self.agent.display_checked.set()
                self.agent.worker.join(timeout=1)
            raise


class DoneAfterDisplayCheckTau(FakeTau):
    def __init__(self):
        super().__init__()
        self.display_checked = threading.Event()
        self.worker_ready = threading.Event()
        self.worker = None

    def put_task(self, prompt, source="user", images=None, events=None):
        self.prompt, self.source, self.events = prompt, source, events
        self.display = DisplayRaceQueue(self)
        return self.display

    def run(self, once=False):
        self.once = once
        self.worker = threading.current_thread()
        self.worker_ready.set()
        self.display_checked.wait(timeout=1)
        self.display.put({"done": "race result"})


def test_runner_done_racing_with_display_check_preserves_result():
    from apps.api.server import TauExecution

    result = TauExecution(DoneAfterDisplayCheckTau, "hello").wait()
    assert result.text == "race result"


class BlockingRunTau(FakeTau):
    def __init__(self):
        super().__init__()
        self.run_started = threading.Event()
        self.release_run = threading.Event()
        self.run_finished = threading.Event()

    def run(self, once=False):
        self.once = once
        self.run_started.set()
        self.release_run.wait(timeout=2)
        self.display.put({"done": ""})
        self.run_finished.set()

    def abort(self):
        self.aborted = True
        self.release_run.set()


class BlockingFactory:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.created = threading.Event()
        self.agent = None

    def __call__(self):
        self.started.set()
        self.release.wait(timeout=2)
        self.agent = BlockingRunTau()
        self.created.set()
        return self.agent


def test_non_streaming_request_cancellation_aborts_execution(monkeypatch):
    agent = BlockingRunTau()
    app = create_app("secret", tau_factory=lambda: agent)
    wait_started = threading.Event()
    original_wait = server.TauExecution.wait

    def tracked_wait(execution):
        wait_started.set()
        return original_wait(execution)

    monkeypatch.setattr(server.TauExecution, "wait", tracked_wait)

    async def cancel_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test",
        ) as client:
            pending = asyncio.create_task(client.post(
                "/v1/chat/completions", headers=_headers(), json={
                    "model": "tau-agent",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            ))
            assert await asyncio.to_thread(agent.run_started.wait, 1)
            assert await asyncio.to_thread(wait_started.wait, 1)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            try:
                assert agent.aborted is True
                assert await asyncio.to_thread(agent.run_finished.wait, 1)
            finally:
                agent.release_run.set()

    asyncio.run(cancel_request())


def test_request_cancelled_during_factory_aborts_eventual_execution():
    factory = BlockingFactory()
    app = create_app("secret", tau_factory=factory)

    async def cancel_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test",
        ) as client:
            pending = asyncio.create_task(client.post(
                "/v1/chat/completions", headers=_headers(), json={
                    "model": "tau-agent",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            ))
            assert await asyncio.to_thread(factory.started.wait, 1)
            pending.cancel()
            await asyncio.sleep(0)
            factory.release.set()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert await asyncio.to_thread(factory.created.wait, 1)
            assert await asyncio.to_thread(factory.agent.run_started.wait, 1)
            try:
                assert factory.agent.aborted is True
                assert await asyncio.to_thread(factory.agent.run_finished.wait, 1)
            finally:
                factory.agent.release_run.set()

    asyncio.run(cancel_request())


class StartupGateTau(FakeTau):
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.stop_sig = False
        self.run_entered = threading.Event()
        self.release_startup = threading.Event()
        self.proceeded = threading.Event()

    def run(self, once=False):
        self.once = once
        self.run_entered.set()
        self.release_startup.wait(timeout=1)
        self.is_running = True
        if not self.stop_sig:
            self.proceeded.set()
        self.display.put({"done": ""})
        self.is_running = False

    def abort(self):
        if not self.is_running:
            return
        self.stop_sig = True


def test_abort_before_tau_is_running_latches_startup_cancellation():
    from apps.api.server import TauExecution

    agent = StartupGateTau()
    execution = TauExecution(lambda: agent, "hello")
    assert agent.run_entered.wait(timeout=1)
    assert agent.is_running is False
    execution.abort()
    agent.release_startup.set()
    execution.wait()
    assert agent.proceeded.is_set() is False


def _asgi_chat_scope(spec_version):
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": spec_version},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/chat/completions",
        "raw_path": b"/v1/chat/completions",
        "query_string": b"",
        "headers": [
            (b"authorization", b"Bearer secret"),
            (b"content-type", b"application/json"),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }


def _asgi_chat_receive(disconnect=False):
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {
                "type": "http.request",
                "body": json.dumps({
                    "model": "tau-agent",
                    "stream": True,
                    "messages": [{"role": "user", "content": "hello"}],
                }).encode(),
                "more_body": False,
            }
        if disconnect:
            return {"type": "http.disconnect"}
        await asyncio.Future()

    return receive


def test_response_start_failure_aborts_before_stream_iteration():
    agent = BlockingRunTau()
    app = create_app("secret", tau_factory=lambda: agent)
    body_started = threading.Event()

    async def send(message):
        if message["type"] == "http.response.start":
            raise RuntimeError("response start failed")
        body_started.set()

    async def fail_response_start():
        with pytest.raises(RuntimeError, match="response start failed"):
            await app(_asgi_chat_scope("2.4"), _asgi_chat_receive(), send)
        assert await asyncio.to_thread(agent.run_started.wait, 1)
        try:
            assert body_started.is_set() is False
            assert agent.aborted is True
            assert await asyncio.to_thread(agent.run_finished.wait, 1)
        finally:
            agent.release_run.set()

    asyncio.run(fail_response_start())


class CountingAbortTau(FakeTau):
    def __init__(self):
        super().__init__()
        self.run_started = threading.Event()
        self.release_run = threading.Event()
        self.abort_calls = 0

    def run(self, once=False):
        self.once = once
        self.run_started.set()
        self.release_run.wait(timeout=1)
        self.display.put({"done": ""})

    def abort(self):
        self.abort_calls += 1


def test_execution_abort_cleanup_is_idempotent():
    from apps.api.server import TauExecution

    agent = CountingAbortTau()
    execution = TauExecution(lambda: agent, "hello")
    assert agent.run_started.wait(timeout=1)
    execution.abort()
    execution.abort()
    agent.release_run.set()
    execution.wait()
    assert agent.abort_calls == 1


def test_asgi_23_immediate_disconnect_aborts_before_stream_iteration():
    agent = BlockingRunTau()
    app = create_app("secret", tau_factory=lambda: agent)
    body_started = threading.Event()

    async def send(message):
        if message["type"] == "http.response.start":
            await asyncio.Future()
        body_started.set()

    async def disconnect_before_body():
        await app(
            _asgi_chat_scope("2.3"), _asgi_chat_receive(disconnect=True), send,
        )
        assert await asyncio.to_thread(agent.run_started.wait, 1)
        try:
            assert body_started.is_set() is False
            assert agent.aborted is True
            assert await asyncio.to_thread(agent.run_finished.wait, 1)
        finally:
            agent.release_run.set()

    asyncio.run(disconnect_before_body())
