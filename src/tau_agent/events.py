"""Typed event contract for the agent run loop.

Stage 0 of the typed-event refactor (issue 1.2): defines the structured events
that will replace agent_runner_loop's rendered-string yields. Nothing consumes
these yet — agent_runner_loop still yields strings. default_render() is a
spec-grade reimplementation of the current verbose string output so that stage 1
(rewiring the loop to yield events) can validate byte-for-byte equivalence via
real-session diff.

Events mirror the yield points in agent_loop.py:
  TurnStarted        <- :54 (turn dict) + :55 (header)
  AssistantTextChunk <- :61 yield from response_gen (LLM token stream)
  AssistantTextDone  <- :62 '\\n\\n'
  ToolCallStart      <- :78 (header + args fence) + :85 (output fence-open)
  ToolOutputChunk    <- :88 yield from proxy (tool execution output)
  ToolCallEnd        <- :87 (output fence-close)
  TurnEnded          <- loop exit
"""
from dataclasses import dataclass

from .agent_loop import get_pretty_json


@dataclass
class TurnStarted:
    """A new agent turn begins.

    task_mode mirrors agent_loop.py:52 ``if handler.parent.task_dir`` — when a
    task dir is set the header shortens to "Turn N ..." (no "LLM Running").
    """

    turn: int
    task_mode: bool = False


@dataclass
class AssistantTextChunk:
    """One chunk of the LLM's streamed reply (token-by-token passthrough)."""

    text: str


@dataclass
class AssistantTextDone:
    """End of this LLM call's assistant text (renders the trailing blank line)."""

    pass


@dataclass
class ToolCallStart:
    """A tool invocation begins — header + args fence + output fence-open."""

    tool_name: str
    args: dict
    tool_id: str = ""


@dataclass
class ToolOutputChunk:
    """One chunk of a tool's streamed output (passthrough)."""

    text: str


@dataclass
class ToolCallEnd:
    """The tool invocation finished — output fence-close."""

    pass


@dataclass
class TurnEnded:
    """The run loop exited (EXITED / CURRENT_TASK_DONE / MAX_TURNS_EXCEEDED)."""

    exit_reason: dict


def render_event(event, verbose: bool = True) -> str:
    """Default string rendering — byte-for-byte golden for agent_runner_loop's
    current verbose output. Stage 1 validates this against real sessions.

    Non-verbose is a separate path (agent_loop.py:63-66 cleans and emits whole);
    only verbose is fully specified here.
    """
    if isinstance(event, TurnStarted):
        turnstr = (
            f"Turn {event.turn} ..."
            if event.task_mode
            else f"LLM Running (Turn {event.turn}) ..."
        )
        if verbose:
            turnstr = f"**{turnstr}**"
        return f"\n\n{turnstr}\n\n"
    if isinstance(event, AssistantTextChunk):
        return event.text
    if isinstance(event, AssistantTextDone):
        return "\n\n" if verbose else ""
    if isinstance(event, ToolCallStart):
        pretty = get_pretty_json(event.args)
        return f"🛠️ Tool: `{event.tool_name}`  📥 args:\n````text\n{pretty}\n````\n`````\n"
    if isinstance(event, ToolOutputChunk):
        return event.text
    if isinstance(event, ToolCallEnd):
        return "`````\n"
    if isinstance(event, TurnEnded):
        return ""
    return ""


def render_events(events, verbose: bool = True):
    """Render a stream of events into a stream of strings.

    Stage 1 adapter: lets taumain keep a string display_queue (issue 1.2
    tradeoff 2) without touching its 5 cmd consumers.
    """
    for event in events:
        yield render_event(event, verbose)
