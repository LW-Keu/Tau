import asyncio, json, os, queue, sys, threading, time, uuid
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from tau_agent.events import render_event
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


@dataclass(frozen=True)
class ExecutionResult:
    text: str
    error: str | None = None


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
        self.display = self.agent.put_task(
            prompt, source="api", events=self.events,
        )
        self.cancelled = threading.Event()
        self.runner = threading.Thread(
            target=self._run, daemon=True,
        )
        self.pump = threading.Thread(target=self._pump, daemon=True)
        self.runner.start()
        self.pump.start()

    def _run(self):
        if self.cancelled.is_set():
            self.display.put({"done": ""})
            return
        try:
            self.agent.run(once=True)
        except Exception as error:
            self.display.put({"done": "", "error": str(error)})

    def _display_done(self):
        while True:
            try:
                item = self.display.get_nowait()
            except queue.Empty:
                return None
            if "done" in item:
                return item

    def _pump(self):
        done = None
        while done is None:
            try:
                event = self.events.get(timeout=0.05)
                text = render_event(event, self.agent.verbose)
                if text:
                    self.output.put(ExecutionEvent("delta", text))
            except queue.Empty:
                pass
            done = self._display_done()
            if done is None and not self.runner.is_alive():
                done = self._display_done() or {"done": ""}
        self.runner.join(timeout=1)
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            text = render_event(event, self.agent.verbose)
            if text:
                self.output.put(ExecutionEvent("delta", text))
        self.output.put(ExecutionEvent(
            "done", done.get("done", ""), done.get("error"),
        ))

    def next_event(self, timeout=0.2):
        try:
            return self.output.get(timeout=timeout)
        except queue.Empty:
            return None

    def wait(self):
        while True:
            event = self.next_event()
            if event and event.kind == "done":
                return ExecutionResult(event.text, event.error)

    def abort(self):
        self.cancelled.set()
        self.agent.stop_sig = True
        self.agent.abort()


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
    if len(chat.messages) == 1:
        return current
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


def _sse(payload):
    value = payload if isinstance(payload, str) else json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"),
    )
    return f"data: {value}\n\n"


def _chunk(completion_id, created, delta=None, finish_reason=None):
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": MODEL_ID,
        "choices": [{
            "index": 0,
            "delta": delta or {},
            "finish_reason": finish_reason,
        }],
    }


async def stream_completion(request, execution):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    finished = False
    try:
        yield _sse(_chunk(completion_id, created, {"role": "assistant"}))
        while not finished:
            if await request.is_disconnected():
                return
            event = await asyncio.to_thread(execution.next_event)
            if event is None:
                continue
            if event.kind == "delta":
                yield _sse(_chunk(
                    completion_id, created, {"content": event.text},
                ))
                continue
            finished = True
            if event.error:
                yield _sse({"error": {
                    "message": event.error,
                    "type": "server_error",
                    "code": "tau_run_failed",
                }})
            else:
                yield _sse(_chunk(
                    completion_id, created, finish_reason="stop",
                ))
            yield _sse("[DONE]")
    finally:
        if not finished:
            execution.abort()


async def _create_execution(tau_factory, prompt):
    construction = asyncio.create_task(asyncio.to_thread(
        TauExecution, tau_factory, prompt,
    ))
    try:
        return await asyncio.shield(construction)
    except asyncio.CancelledError:
        try:
            execution = await asyncio.shield(construction)
        except Exception:
            pass
        else:
            await asyncio.to_thread(execution.abort)
        raise


def create_app(api_key, tau_factory=Tau):
    if not api_key:
        raise ValueError("TAU_API_KEY must be set")
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
    async def health():
        return {"status": "ok"}

    @app.get("/v1/models")
    async def models(request: Request):
        authorize(request)
        return {"object": "list", "data": [{
            "id": MODEL_ID, "object": "model", "created": 0,
            "owned_by": "tau",
        }]}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        authorize(request)
        try:
            payload = await request.json()
        except ValueError:
            raise APIError(400, "Request body must be valid JSON", code="invalid_json")
        chat = parse_chat(payload)
        try:
            execution = await _create_execution(
                app.state.tau_factory, build_prompt(chat),
            )
        except Exception as error:
            raise APIError(500, str(error), "server_error", "tau_init_failed")
        if chat.stream:
            return StreamingResponse(
                stream_completion(request, execution),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        result = await asyncio.to_thread(execution.wait)
        if result.error:
            raise APIError(500, result.error, "server_error", "tau_run_failed")
        return _completion(result)

    return app
