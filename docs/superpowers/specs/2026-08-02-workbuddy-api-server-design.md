# WorkBuddy-Compatible Tau API Server Design

## Goal

Expose Tau as a local OpenAI-compatible agent endpoint so WorkBuddy can use
Tau as a custom model. Tau keeps its full local toolset; WorkBuddy supplies the
chat UI and sends the visible conversation history with each request.

The first version is intentionally local, single-user, text-only, and
stateless across HTTP requests.

## Success Criteria

- `TAU_API_KEY=... tau api` starts the service on `127.0.0.1:8642`.
- WorkBuddy can discover `tau-agent` through `GET /v1/models`.
- WorkBuddy can call `POST /v1/chat/completions` in streaming and non-streaming
  modes.
- Streaming shows Tau's reasoning progress, tool calls, tool output, and final
  answer as ordinary assistant text deltas.
- Separate WorkBuddy conversations and concurrent requests never share a Tau
  instance, history, output queue, or abort signal.
- Disconnecting one request aborts only that request's Tau instance.

## Non-Goals

- OpenAI Responses API compatibility
- Server-side conversation persistence or session management
- Images, attachments, audio, or other multimodal input
- Remote or multi-user deployment
- CORS configuration
- Structured OpenAI tool-call output for Tau's internal tools
- Usage accounting, model sampling controls, or client-selected Tau backends

## Architecture

Add `apps/api/` as a frontend channel alongside the existing TUI, GUI, Web,
and IM channels. The API adapter owns HTTP concerns only: authentication,
validation, message conversion, OpenAI response envelopes, SSE framing, and
request lifecycle management.

Each completion request creates and runs an independent `Tau` instance. The
adapter submits work through `Tau.put_task`; it does not call the configured
LLM backend or the agent loop directly.

```text
WorkBuddy -> apps/api -> Tau.put_task -> tau_agent
                         <- queues <-
```

The adapter consumes the typed event queue for incremental text and the
existing `display_queue` as the authoritative completion/error channel. This
preserves Tau's current frontend contracts and avoids changing the agent loop.

## Components and Files

- `apps/api/__init__.py`: package marker.
- `apps/api/server.py`: FastAPI application, request models, authentication,
  history conversion, per-request Tau runner, SSE encoding, and CLI entry.
- `src/tau_coding/taumain.py`: add an opt-in one-task run mode so a
  request-owned Tau runner exits after its completion; the default remains the
  existing persistent frontend loop.
- `src/tau_coding/commands/_launchers.py`: register the `tau api` launcher.
- `pyproject.toml`: add an `api` optional dependency group and include FastAPI
  and uvicorn in the existing `ui` and `all-apps` groups.
- `tests/test_api_server.py`: protocol, isolation, lifecycle, and error tests.
- `README.md`: startup and WorkBuddy custom-model configuration.

No new runtime abstraction is added to `src/tau_agent` or `src/tau_coding`.

## Startup and Configuration

The only supported public startup path is:

```bash
TAU_API_KEY=your-local-key tau api
```

Defaults:

| Setting | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `8642` |
| Model ID | `tau-agent` |
| Base URL | `http://127.0.0.1:8642/v1` |

`--port` may override the port. The first version does not expose a host flag;
this prevents accidental network exposure of an agent with terminal and file
access.

`TAU_API_KEY` must be non-empty. `tau api` refuses to start otherwise and
prints a direct setup instruction. All `/v1/*` endpoints require
`Authorization: Bearer <TAU_API_KEY>`. `/health` is unauthenticated.

## HTTP Contract

### `GET /health`

Returns a small JSON object indicating that the HTTP process is ready. It does
not initialize an agent or probe the upstream model.

### `GET /v1/models`

Returns an OpenAI list envelope containing exactly one model with ID
`tau-agent`.

### `POST /v1/chat/completions`

Accepted fields:

- `model`: must equal `tau-agent`.
- `messages`: a non-empty list of text-only `system`, `user`, and `assistant`
  messages. The final message must be a non-empty `user` message.
- `stream`: optional boolean, default `false`.

Unknown fields and common model controls such as `temperature`, `top_p`,
`max_tokens`, and `tools` are accepted and ignored. Tau's configured backend
and internal tools remain authoritative.

String content is the only supported content representation. Content-part
arrays, images, attachments, and unsupported roles return `400` rather than
being silently discarded.

Non-streaming replies use a standard `chat.completion` envelope with one
assistant choice and `finish_reason: "stop"`. Token usage is omitted because
Tau cannot currently report reliable end-to-end counts across its agent turns.

Streaming replies use `text/event-stream`. The sequence is:

1. A `chat.completion.chunk` assigning the `assistant` role.
2. Zero or more chunks containing text deltas.
3. A final chunk with no content and `finish_reason: "stop"`.
4. `data: [DONE]`.

All chunks for one request share an ID, model ID, and creation timestamp.

## Conversation Conversion

The API is stateless. WorkBuddy's visible history is converted into the current
Tau task rather than written into a cached Tau backend.

The final user message becomes the current request. Earlier messages become a
role-labelled context section:

```text
The following prior conversation was supplied by WorkBuddy. Use it only to
continue the current context.

[SYSTEM]
...

[USER]
...

[ASSISTANT]
...

Current user request:
...
```

Tau's built-in system prompt remains authoritative. A WorkBuddy `system`
message is an additional client instruction, not a replacement for Tau's
runtime, tool, or safety instructions.

This design deliberately does not preserve Tau's native tool-call history or
temporary working memory across HTTP requests. Those details are absent from
the OpenAI-visible history that WorkBuddy sends back. A single request still
supports Tau's full multi-turn agent loop and tool use.

## Execution and Streaming

For each request the adapter:

1. Authenticates and validates the complete request before starting the stream.
2. Builds the current Tau task from the supplied messages.
3. Creates a fresh `Tau`, enables incremental output, and starts
   `Tau.run(once=True)` in a request-owned daemon thread. The opt-in `once`
   mode exits after exactly one queued task; existing callers of `Tau.run()`
   retain their persistent worker behavior.
4. Calls `put_task` with an event queue and retains the returned display queue.
5. Renders typed events into ordinary text deltas while monitoring the display
   queue for authoritative completion or failure.
6. Emits the final OpenAI chunk/envelope and releases all request-owned state.

Only rendered events are emitted as live progress. The adapter accumulates
that emitted text; when `display_queue` supplies its final `done` value, the
adapter emits only a missing suffix, if any. This makes the display queue an
authoritative terminal/error signal without duplicating normal event text.
Non-streaming requests use the final display value directly.

Queue reads must not block the async server loop. A small async bridge may use
thread offloading, but it must remain request-local and bounded by the request
lifecycle.

When the client disconnects or the response coroutine is cancelled, the
adapter calls `abort()` on that request's Tau instance. It never accesses a
global current agent.

## Errors

Before response streaming begins, errors use an OpenAI-style JSON envelope:

```json
{
  "error": {
    "message": "...",
    "type": "invalid_request_error",
    "code": "..."
  }
}
```

Expected status codes:

- `400`: malformed messages, unsupported content, unsupported role, or model
- `401`: missing or incorrect Bearer token
- `500`: Tau initialization failure

After SSE headers have been sent, the status code cannot change. A runtime
failure is emitted as an OpenAI-style error object in an SSE `data` frame,
followed by `[DONE]`. No non-standard `finish_reason` value is introduced.

The service has no independent wall-clock timeout in the first version. Tau's
existing turn limit and explicit abort behavior remain authoritative.

## Concurrency and Isolation

There is no global `Tau` instance and no session cache. Each request owns:

- one `Tau` instance
- one runner thread
- one event queue
- one display queue
- one completion ID
- one cancellation path

This permits independent concurrent requests while preventing history,
progress, or stop signals from crossing conversation boundaries. Resource
limits and admission control are deferred because the first version is local
and single-user.

## Verification

Automated tests use an injected fake Tau factory; they do not require a real
LLM key or network call. Coverage includes:

- startup rejection without `TAU_API_KEY`
- successful and failed Bearer authentication
- `/health` and `/v1/models` shapes
- WorkBuddy-style request parsing
- role-labelled multi-turn history conversion
- standard non-streaming response shape
- SSE role, content, terminal, and `[DONE]` frames
- incremental rendering of Tau tool-progress text
- explicit `400` responses for non-text input
- isolation of two concurrent requests
- request-local abort on disconnect
- initialization and runtime failure envelopes

After automated tests pass, perform a real local smoke test:

1. Start `TAU_API_KEY=test-key tau api`.
2. Call `/v1/models` with `curl`.
3. Call `/v1/chat/completions` once with `stream: false`.
4. Call it once with `stream: true` and confirm progress arrives before the
   final answer.
5. Configure WorkBuddy Custom Model with the base URL, key, and `tau-agent`,
   then run one tool-using task as manual acceptance.

## Deferred Extensions

Future versions may add stable server-side session IDs, persisted native Tau
history, multimodal input, remote binding with stronger security, structured
tool events, or the OpenAI Responses API. None is required for the WorkBuddy
first version and none should shape the initial implementation beyond keeping
the HTTP adapter isolated from the agent core.
