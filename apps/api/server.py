import os, sys, time, uuid
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

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

    return app
