# WorkBuddy-Compatible Tau API Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local `tau api` service that lets WorkBuddy use a fully tool-equipped Tau agent through OpenAI Chat Completions.

**Architecture:** `apps/api/server.py` is a stateless OpenAI/FastAPI adapter. Every completion owns a fresh `Tau` instance running exactly one task; typed events provide live SSE text, while `display_queue` provides the authoritative final result and structured failure metadata.

**Tech Stack:** Python 3.10–3.13, FastAPI ≥0.110, uvicorn ≥0.29, standard-library queues/threads/asyncio, pytest through `uv`.

## Global Constraints

- Bind only to `127.0.0.1`; expose no host override in the first version.
- Default port is `8642`; `--port` is the only network option.
- Advertise exactly one model ID: `tau-agent`.
- Require non-empty `TAU_API_KEY` for startup and Bearer authentication on `/v1/*`.
- Accept only string content with `system`, `user`, and `assistant` roles; reject multimodal content.
- Keep requests stateless and isolate every request in its own Tau instance, queues, runner thread, and abort path.
- Do not add dependencies outside FastAPI and uvicorn; use `uv`, never pip/venv/poetry.
- Do not move existing packages or replace the permanent `display_queue`/`event_queue` contracts.
- Preserve all current `Tau.run()` callers by making one-task execution opt-in.

## File Map

- Create `apps/api/__init__.py`: declare the API frontend package.
- Create `apps/api/server.py`: protocol validation, app factory, Tau execution bridge, completion/SSE envelopes, and uvicorn CLI.
- Create `tests/test_api_server.py`: protocol, bridge, streaming, isolation, and launcher behavior.
- Modify `src/tau_coding/taumain.py:147-211`: opt-in `run(once=True)` lifecycle and additive `error` metadata.
- Modify `src/tau_coding/commands/_launchers.py:18-55`: register `api` in the launcher table.
- Modify `pyproject.toml:22-51`: add the focused `api` optional extra.
- Modify `README.md:89-104,117-130`: document startup and WorkBuddy configuration.
- Modify `docs/superpowers/specs/2026-08-02-workbuddy-api-server-design.md`: retain the planning-discovered one-task lifecycle requirement.

---

### Task 1: Give Tau a one-task worker lifecycle

**Files:**
- Modify: `src/tau_coding/taumain.py:147-211`
- Test: `tests/test_api_server.py`

**Interfaces:**
- Consumes: existing `Tau.task_queue`, `Tau.put_task(...)`, and display/event queue contracts.
- Produces: `Tau.run(once: bool = False) -> None`; display `done` items may include `error: str` on backend failure.

- [ ] **Step 1: Write failing lifecycle tests**

Create `tests/test_api_server.py` with a small Tau harness that avoids real configuration and assert both the opt-in exit and additive error signal:

```python
import queue
import threading

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
```

- [ ] **Step 2: Run the tests and verify the intended failures**

Run:

```bash
uv run pytest tests/test_api_server.py -v
```

Expected: `test_tau_run_once_exits_after_one_task` fails because `run()` does not accept `once`; the error-metadata test fails because `done["error"]` is absent.

- [ ] **Step 3: Implement the minimal compatible lifecycle change**

Change the worker signature and the two exit points in `Tau.run`:

```python
def run(self, once=False):
    while True:
        task = self.task_queue.get()
        # existing task setup
        raw_query = self._handle_slash_cmd(raw_query, event_queue)
        if raw_query is None:
            self.task_queue.task_done()
            if once: return
            continue
        # existing agent execution remains unchanged
```

In the existing backend exception branch, compute the formatted error once and expose it additively:

```python
except Exception as e:
    error = format_error(e)
    print(f"Backend Error: {error}")
    display_queue.put({
        "done": full_resp + f"\n```\n{error}\n```",
        "error": error,
        "source": source,
        "turn": curr_turn,
        "outputs": turn_resps.copy(),
    })
```

After the existing `finally` block has called `task_done()` and stopped tool subprocesses, exit only the opt-in worker:

```python
if once:
    return
```

- [ ] **Step 4: Verify lifecycle behavior and current Tau regressions**

Run:

```bash
uv run pytest tests/test_api_server.py tests/test_tau_agent_loop_events_diff.py tests/test_tau_agent_handler_host.py -v
```

Expected: all selected tests pass; calls to `Tau.run()` without arguments retain the infinite frontend worker behavior.

- [ ] **Step 5: Commit the lifecycle seam**

```bash
git add src/tau_coding/taumain.py tests/test_api_server.py docs/superpowers/specs/2026-08-02-workbuddy-api-server-design.md
git commit -m "feat: add one-task Tau worker mode"
```

---

### Task 2: Add the OpenAI-compatible protocol shell

**Files:**
- Create: `apps/api/__init__.py`
- Create: `apps/api/server.py`
- Modify: `pyproject.toml:22-51`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Consumes: `Tau` as the default factory, but does not instantiate it for health/model discovery.
- Produces: `APIError`, `ChatInput`, `parse_chat(payload)`, `build_prompt(chat)`, and `create_app(api_key, tau_factory)`.

- [ ] **Step 1: Declare and install the focused API dependency extra**

Add this group before `ui` in `pyproject.toml`; leave the already-present UI/all-app dependency entries unchanged:

```toml
api = [
    "fastapi>=0.110",
    "uvicorn>=0.29",
]
```

Run:

```bash
uv sync --extra api
```

Expected: dependency resolution succeeds and FastAPI/uvicorn are importable.

- [ ] **Step 2: Write failing protocol tests**

Append tests that cover auth, model discovery, validation, and deterministic history conversion:

```python
import pytest
from fastapi.testclient import TestClient

from apps.api.server import APIError, build_prompt, create_app, parse_chat


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
```

- [ ] **Step 3: Run protocol tests to verify import/behavior failures**

Run:

```bash
uv run pytest tests/test_api_server.py -k "health or parse_chat or build_prompt" -v
```

Expected: collection fails because `apps.api.server` does not exist.

- [ ] **Step 4: Implement the protocol primitives and read-only endpoints**

Create an empty `apps/api/__init__.py`. In `apps/api/server.py`, bootstrap the repository path in the same manner as `apps/web/conductor.py`, then define focused protocol types and validation:

```python
import os, sys, time, uuid
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path: sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tau_coding.taumain import Tau

MODEL_ID = "tau-agent"


class APIError(Exception):
    def __init__(self, status, message, error_type="invalid_request_error",
                 code="invalid_request"):
        self.status, self.message = status, message
        self.error_type, self.code = error_type, code


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatInput:
    model: str
    messages: tuple[ChatMessage, ...]
    stream: bool = False


def parse_chat(payload):
    if not isinstance(payload, dict):
        raise APIError(400, "Request body must be a JSON object")
    if payload.get("model") != MODEL_ID:
        raise APIError(400, f"Unsupported model: {payload.get('model')!r}",
                       code="model_not_found")
    raw = payload.get("messages")
    if not isinstance(raw, list) or not raw:
        raise APIError(400, "messages must be a non-empty list")
    messages = []
    for item in raw:
        if not isinstance(item, dict) or item.get("role") not in {
            "system", "user", "assistant",
        }:
            raise APIError(400, "Only system, user, and assistant roles are supported",
                           code="unsupported_role")
        content = item.get("content")
        if not isinstance(content, str):
            raise APIError(400, "Only string message content is supported",
                           code="unsupported_content")
        messages.append(ChatMessage(item["role"], content))
    if messages[-1].role != "user" or not messages[-1].content.strip():
        raise APIError(400, "The final message must be a non-empty user message",
                       code="invalid_messages")
    stream = payload.get("stream", False)
    if not isinstance(stream, bool):
        raise APIError(400, "stream must be a boolean", code="invalid_stream")
    return ChatInput(MODEL_ID, tuple(messages), stream)


def build_prompt(chat):
    current = chat.messages[-1].content
    if len(chat.messages) == 1: return current
    history = "\n\n".join(
        f"[{message.role.upper()}]\n{message.content}"
        for message in chat.messages[:-1]
    )
    return (
        "The following prior conversation was supplied by WorkBuddy. "
        "Use it only to continue the current context.\n\n"
        f"{history}\n\nCurrent user request:\n{current}"
    )


def _error_response(error):
    return JSONResponse({"error": {
        "message": error.message, "type": error.error_type,
        "code": error.code,
    }}, status_code=error.status)


def create_app(api_key, tau_factory=Tau):
    if not api_key: raise ValueError("TAU_API_KEY must be set")
    app = FastAPI(title="Tau Agent API")
    app.state.tau_factory = tau_factory

    @app.exception_handler(APIError)
    async def handle_api_error(request, error):
        return _error_response(error)

    def authorize(request):
        if request.headers.get("authorization") != f"Bearer {api_key}":
            raise APIError(401, "Invalid API key", "authentication_error",
                           "invalid_api_key")

    @app.get("/health")
    async def health(): return {"status": "ok"}

    @app.get("/v1/models")
    async def models(request: Request):
        authorize(request)
        return {"object": "list", "data": [{
            "id": MODEL_ID, "object": "model", "created": 0,
            "owned_by": "tau",
        }]}

    return app
```

Keep `time` and `uuid` imports for the completion helpers added in Task 3.

- [ ] **Step 5: Run protocol and existing CLI tests**

Run:

```bash
uv run pytest tests/test_api_server.py tests/test_tau_coding_package.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit the protocol shell**

```bash
git add apps/api/__init__.py apps/api/server.py pyproject.toml uv.lock tests/test_api_server.py
git commit -m "feat: add WorkBuddy API protocol shell"
```

---

### Task 3: Bridge one Tau task into a non-streaming completion

**Files:**
- Modify: `apps/api/server.py`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Consumes: `Tau.run(once=True)`, `Tau.put_task(..., events=queue.Queue())`, `render_event`, and display `done/error` fields.
- Produces: `TauExecution(tau_factory, prompt)`, `TauExecution.wait() -> ExecutionResult`, and non-streaming `/v1/chat/completions`.

- [ ] **Step 1: Write failing execution and non-streaming tests**

Append a deterministic fake agent and tests:

```python
from tau_agent.events import RawText, TurnEnded


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
        if self.error: item["error"] = self.error
        else: self.events.put(TurnEnded({"result": "done"}))
        self.display.put(item)

    def abort(self): self.aborted = True


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


def test_tau_initialization_failure_is_openai_error():
    def fail_init(): raise RuntimeError("invalid Tau config")
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
```

- [ ] **Step 2: Run the new tests and verify endpoint failure**

Run:

```bash
uv run pytest tests/test_api_server.py -k "non_streaming" -v
```

Expected: both tests fail with `404` because `/v1/chat/completions` is not registered.

- [ ] **Step 3: Implement the request-owned execution bridge**

Add these imports and types to `apps/api/server.py`:

```python
import queue, threading
from dataclasses import dataclass

from tau_agent.events import TurnEnded, render_event


@dataclass(frozen=True)
class ExecutionResult:
    text: str
    error: str | None = None


class TauExecution:
    def __init__(self, tau_factory, prompt):
        self.agent = tau_factory()
        self.agent.inc_out = True
        self.events = queue.Queue()
        self.display = self.agent.put_task(
            prompt, source="api", events=self.events,
        )
        self.runner = threading.Thread(
            target=self.agent.run, kwargs={"once": True}, daemon=True,
        )
        self.runner.start()

    def wait(self):
        while True:
            item = self.display.get()
            if "done" in item:
                self.runner.join(timeout=1)
                return ExecutionResult(item.get("done", ""), item.get("error"))

    def abort(self):
        self.agent.abort()
```

Task 4 will extend this class with the event pump; do not add a global agent or executor.

- [ ] **Step 4: Add completion envelope helpers and the POST endpoint**

Inside `create_app`, parse JSON explicitly so validation errors keep the OpenAI envelope, initialize Tau before returning a streaming response, and implement the non-stream path:

```python
def _completion(result):
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result.text},
            "finish_reason": "stop",
        }],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    authorize(request)
    try: payload = await request.json()
    except ValueError:
        raise APIError(400, "Request body must be valid JSON", code="invalid_json")
    chat = parse_chat(payload)
    try:
        execution = await asyncio.to_thread(
            TauExecution, app.state.tau_factory, build_prompt(chat),
        )
    except Exception as error:
        raise APIError(500, str(error), "server_error", "tau_init_failed")
    if chat.stream:
        raise APIError(501, "Streaming is not available in this slice",
                       "server_error", "streaming_unavailable")
    result = await asyncio.to_thread(execution.wait)
    if result.error:
        raise APIError(500, result.error, "server_error", "tau_run_failed")
    return _completion(result)
```

Add the `asyncio` import. Task 4 replaces the explicit streaming rejection
with `StreamingResponse` after the SSE generator exists.

- [ ] **Step 5: Verify non-streaming behavior**

Run:

```bash
uv run pytest tests/test_api_server.py -k "not streaming" -v
```

Expected: all lifecycle, protocol, and non-streaming tests pass.

- [ ] **Step 6: Commit the working non-streaming slice**

```bash
git add apps/api/server.py tests/test_api_server.py
git commit -m "feat: run Tau through chat completions"
```

---

### Task 4: Stream typed Tau events with cancellation and isolation

**Files:**
- Modify: `apps/api/server.py`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Consumes: Task 3 `TauExecution` and OpenAI completion metadata.
- Produces: `TauExecution.next_event(timeout)`, request-local cancellation, SSE `chat.completion.chunk` frames, OpenAI error frames, and `[DONE]`.

- [ ] **Step 1: Write failing SSE, error, and isolation tests**

Append tests that parse SSE frames and prove factories are called once per request:

```python
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor


def _sse_payloads(text):
    return [line[6:] for line in text.splitlines() if line.startswith("data: ")]


def test_streaming_completion_emits_role_progress_terminal_and_done():
    client = TestClient(create_app("secret", tau_factory=FakeTau))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    payloads = _sse_payloads(response.text)
    chunks = [json.loads(value) for value in payloads[:-1]]
    assert chunks[0]["choices"][0]["delta"] == {"role": "assistant"}
    assert "final answer" in "".join(
        item["choices"][0]["delta"].get("content", "")
        for item in chunks if "choices" in item
    )
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    assert payloads[-1] == "[DONE]"


def test_streaming_runtime_failure_uses_error_frame_then_done():
    client = TestClient(create_app(
        "secret", tau_factory=lambda: FakeTau(error="backend exploded"),
    ))
    response = client.post("/v1/chat/completions", headers=_headers(), json={
        "model": "tau-agent", "stream": True,
        "messages": [{"role": "user", "content": "hello"}],
    })
    payloads = _sse_payloads(response.text)
    assert json.loads(payloads[-2])["error"]["message"] == "backend exploded"
    assert payloads[-1] == "[DONE]"


def test_concurrent_requests_create_isolated_tau_instances():
    FakeTau.instances.clear()
    app = create_app("secret", tau_factory=FakeTau)
    body = {"model": "tau-agent", "messages": [
        {"role": "user", "content": "hello"},
    ]}
    def post(_):
        with TestClient(app) as client:
            return client.post("/v1/chat/completions", headers=_headers(), json=body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(post, range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert len(FakeTau.instances) == 2
    assert FakeTau.instances[0] is not FakeTau.instances[1]
    assert FakeTau.instances[0].events is not FakeTau.instances[1].events


def test_abort_is_request_local():
    first, second = FakeTau(), FakeTau()
    from apps.api.server import TauExecution
    run_one = TauExecution(lambda: first, "one")
    run_two = TauExecution(lambda: second, "two")
    run_one.abort()
    assert first.aborted is True
    assert second.aborted is False
    assert run_two.wait().text == "final answer"


def test_stream_disconnect_aborts_only_its_execution():
    from apps.api.server import TauExecution, stream_completion

    class DisconnectedRequest:
        async def is_disconnected(self): return True

    first, second = FakeTau(), FakeTau()
    run_one = TauExecution(lambda: first, "one")
    run_two = TauExecution(lambda: second, "two")

    async def consume_disconnected_stream():
        return [frame async for frame in stream_completion(
            DisconnectedRequest(), run_one,
        )]

    asyncio.run(consume_disconnected_stream())
    assert first.aborted is True
    assert second.aborted is False
    assert run_two.wait().text == "final answer"
```

- [ ] **Step 2: Run streaming tests and verify the non-streaming slice fails them**

Run:

```bash
uv run pytest tests/test_api_server.py -k "streaming or concurrent or abort" -v
```

Expected: streaming tests receive Task 3's `501` response instead of SSE
chunks; isolation tests may already pass.

- [ ] **Step 3: Extend TauExecution with a request-local typed-event pump**

Add an output queue and a daemon pump thread. The pump emits rendered events only; it uses `display_queue` solely for the terminal result/error, so the two contracts cannot duplicate text:

```python
@dataclass(frozen=True)
class ExecutionEvent:
    kind: str
    text: str = ""
    error: str | None = None


class TauExecution:
    def __init__(self, tau_factory, prompt):
        self.agent = tau_factory()
        self.agent.inc_out = True
        self.events, self.output = queue.Queue(), queue.Queue()
        self.display = self.agent.put_task(prompt, source="api", events=self.events)
        self.runner = threading.Thread(
            target=self.agent.run, kwargs={"once": True}, daemon=True,
        )
        self.pump = threading.Thread(target=self._pump, daemon=True)
        self.runner.start(); self.pump.start()

    def _pump(self):
        done = None
        while done is None:
            try:
                event = self.events.get(timeout=0.05)
                text = render_event(event, self.agent.verbose)
                if text: self.output.put(ExecutionEvent("delta", text))
            except queue.Empty:
                pass
            while True:
                try: item = self.display.get_nowait()
                except queue.Empty: break
                if "done" in item:
                    done = item
                    break
            if done is None and not self.runner.is_alive():
                done = {"done": ""}
        while True:
            try: event = self.events.get_nowait()
            except queue.Empty: break
            text = render_event(event, self.agent.verbose)
            if text: self.output.put(ExecutionEvent("delta", text))
        self.runner.join(timeout=1)
        self.output.put(ExecutionEvent(
            "done", done.get("done", ""), done.get("error"),
        ))

    def next_event(self, timeout=0.2):
        try: return self.output.get(timeout=timeout)
        except queue.Empty: return None

    def wait(self):
        while True:
            event = self.next_event()
            if event and event.kind == "done":
                return ExecutionResult(event.text, event.error)

    def abort(self): self.agent.abort()
```

- [ ] **Step 4: Implement OpenAI SSE framing and disconnect checks**

Add JSON encoding and helper functions:

```python
import json


def _sse(payload):
    value = payload if isinstance(payload, str) else json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"),
    )
    return f"data: {value}\n\n"


def _chunk(completion_id, created, delta=None, finish_reason=None):
    return {
        "id": completion_id, "object": "chat.completion.chunk",
        "created": created, "model": MODEL_ID,
        "choices": [{"index": 0, "delta": delta or {},
                     "finish_reason": finish_reason}],
    }


async def stream_completion(request, execution):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    yield _sse(_chunk(completion_id, created, {"role": "assistant"}))
    finished = False
    try:
        while not finished:
            if await request.is_disconnected():
                execution.abort()
                return
            event = await asyncio.to_thread(execution.next_event)
            if event is None: continue
            if event.kind == "delta":
                yield _sse(_chunk(completion_id, created,
                                  {"content": event.text}))
                continue
            finished = True
            if event.error:
                yield _sse({"error": {
                    "message": event.error, "type": "server_error",
                    "code": "tau_run_failed",
                }})
            else:
                yield _sse(_chunk(completion_id, created,
                                  finish_reason="stop"))
            yield _sse("[DONE]")
    finally:
        if not finished: execution.abort()
```

Set these response headers when returning `StreamingResponse`:

```python
headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
```

Replace Task 3's `501` branch with:

```python
if chat.stream:
    return StreamingResponse(
        stream_completion(request, execution),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 5: Run API tests and the event-contract regression suite**

Run:

```bash
uv run pytest tests/test_api_server.py tests/test_tau_agent_loop_events_diff.py tests/test_event_projection.py -v
```

Expected: all tests pass; streaming content contains one copy of each fake event and ends with `[DONE]`.

- [ ] **Step 6: Commit streaming and isolation**

```bash
git add apps/api/server.py tests/test_api_server.py
git commit -m "feat: stream isolated Tau API runs"
```

---

### Task 5: Add the `tau api` launcher and WorkBuddy instructions

**Files:**
- Modify: `apps/api/server.py`
- Modify: `src/tau_coding/commands/_launchers.py:18-55`
- Modify: `README.md:89-104,117-130`
- Modify: `tests/test_api_server.py`

**Interfaces:**
- Consumes: `create_app(api_key, Tau)` and the existing data-driven launcher expansion.
- Produces: `main(argv=None)`, `tau api [--port PORT]`, and user-facing WorkBuddy setup instructions.

- [ ] **Step 1: Write failing CLI configuration tests**

Append tests for startup safety and launcher registration:

```python
import pytest

from apps.api import server
from tau_coding.commands._launchers import LAUNCHERS


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
    monkeypatch.setattr(server.uvicorn, "run",
                        lambda app, **kwargs: called.update(kwargs))
    server.main(["--port", "9001"])
    assert called == {"host": "127.0.0.1", "port": 9001}
```

- [ ] **Step 2: Run the CLI tests and verify missing interfaces**

Run:

```bash
uv run pytest tests/test_api_server.py -k "launcher or main" -v
```

Expected: failures because `api` is absent from `LAUNCHERS` and `server.main` is undefined.

- [ ] **Step 3: Register the launcher and implement the safe CLI**

Add this entry to `LAUNCHERS`:

```python
"api": {
    "name": "api",
    "help": "启动 WorkBuddy 兼容 API (api/server.py)",
    "desc": "在本机启动 OpenAI 兼容的 Tau Agent API 服务",
    "cmd": ["python", "{APPS}/api/server.py"],
},
```

Add the server CLI and module guard:

```python
import argparse
import uvicorn


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tau WorkBuddy-compatible API")
    parser.add_argument("--port", type=int, default=8642)
    args = parser.parse_args(argv)
    api_key = os.environ.get("TAU_API_KEY", "").strip()
    if not api_key:
        parser.error("TAU_API_KEY is required; set it before running `tau api`")
    uvicorn.run(create_app(api_key), host="127.0.0.1", port=args.port)


if __name__ == "__main__": main()
```

- [ ] **Step 4: Document exact WorkBuddy configuration and limitations**

Add `tau api` to the README launch examples and frontend table. Add a short section after the table containing:

````markdown
### WorkBuddy 接入

安装 API 依赖并启动本机服务：

```bash
uv pip install -e ".[api]"
TAU_API_KEY=请设置一个本机密钥 tau api
```

在 WorkBuddy 的「自定义模型 / Custom Model」中填写：

- API URL：`http://127.0.0.1:8642/v1`
- API Key：与 `TAU_API_KEY` 相同
- Model：`tau-agent`

首版仅支持本机、纯文本输入。WorkBuddy 的不同对话相互隔离；历史由
WorkBuddy 随请求提供，Tau 的内部工具调用记录不跨请求保存。
````

Keep the nested bash fence valid by using four backticks around this snippet when editing the README.

- [ ] **Step 5: Run focused and full automated verification**

Run:

```bash
uv run pytest tests/test_api_server.py tests/test_tau_coding_package.py -v
uv run pytest -q
```

Expected: focused tests pass; then the full suite exits `0` with no regressions.

- [ ] **Step 6: Perform a real local protocol smoke test**

Start the service in terminal one:

```bash
TAU_API_KEY=test-key uv run python apps/api/server.py --port 8642
```

In terminal two, verify discovery:

```bash
curl -s http://127.0.0.1:8642/v1/models \
  -H 'Authorization: Bearer test-key'
```

Expected: a model-list JSON object containing `"id":"tau-agent"`.

Verify streaming with the locally configured real Tau backend:

```bash
curl -N http://127.0.0.1:8642/v1/chat/completions \
  -H 'Authorization: Bearer test-key' \
  -H 'Content-Type: application/json' \
  -d '{"model":"tau-agent","stream":true,"messages":[{"role":"user","content":"只回复 API OK，不调用工具"}]}'
```

Expected: multiple `data:` frames, a terminal chunk with `"finish_reason":"stop"`, and `data: [DONE]`.

Stop the foreground server with Ctrl-C. Configure WorkBuddy with the documented URL/key/model and send one harmless tool-using request, such as asking Tau to list the current working directory. Confirm progress appears before the final response.

- [ ] **Step 7: Commit launcher and documentation**

```bash
git add apps/api/server.py src/tau_coding/commands/_launchers.py README.md tests/test_api_server.py
git commit -m "docs: add WorkBuddy API startup guide"
```

---

### Task 6: Final standards and completion gate

**Files:**
- Review only: all files changed by Tasks 1–5

**Interfaces:**
- Consumes: the complete feature and its verification evidence.
- Produces: a review-ready branch with no uncommitted generated files.

- [ ] **Step 1: Review the diff against Tau's four code-quality questions**

Run:

```bash
git diff HEAD~5 --check
git diff HEAD~5 --stat
git status --short
```

Expected: no whitespace errors; the diff is limited to the files in this plan; only intentional plan-document changes may remain uncommitted.

Check explicitly:

1. API protocol changes stay local to `apps/api/server.py`.
2. New frontends require no changes to the Tau agent loop beyond the generic `once` lifecycle flag and additive error metadata.
3. Every request-owned resource is created and cancelled together.
4. Authentication, initialization failures, and run failures identify the responsible boundary.

- [ ] **Step 2: Run the final verification command from a clean process**

```bash
uv run pytest -q
```

Expected: exit code `0`; record the exact passed/skipped counts in the handoff.

- [ ] **Step 3: Commit any review-only corrections**

If review required a correction, stage only its named files and commit it with:

```bash
git commit -m "fix: tighten WorkBuddy API compatibility"
```

If no correction was required, do not create an empty commit.
