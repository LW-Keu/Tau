"""Typed event contract for the agent run loop.

Stage 0/1 of the typed-event refactor (issue 1.2): defines the structured
events that will replace agent_runner_loop's rendered-string yields.
default_render() is a spec-grade reimplementation of the current verbose string
output so stage 1 can validate byte-for-byte equivalence via real-session diff.

Events mirror the yield points in agent_loop.py:
  TurnStarted        <- :54 (turn dict) + :55 (header)
  AssistantTextChunk <- :61 yield from response_gen (LLM token stream)
  AssistantTextDone  <- :62 '\\n\\n'
  ToolCallStart      <- :78 (🛠️ header + args fence) — header only
  ToolOutputStart    <- :85 (output fence-open) — gated behind tool yielding
  ToolOutputChunk    <- :88 yield from proxy (tool execution output)
  ToolOutputEnd      <- :87 (output fence-close)
  RawText            <- non-verbose path (passthrough, not yet structured)
  TurnEnded          <- loop exit

ToolOutputStart is split from ToolCallStart because agent_loop.py:85 only fires
after ``v = next(gen)`` succeeds — a tool that returns without yielding emits
no fence. Keeping them separate lets render stay faithful to that case.
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
    """A tool invocation begins — renders the header + args fence (agent_loop.py:78).

    The output fence-open (:85) is a separate ToolOutputStart event because it
    only fires when the tool actually yields (gated behind ``v = next(gen)``).
    """

    tool_name: str
    args: dict
    tool_id: str = ""


@dataclass
class ToolOutputStart:
    """Output fence-open (agent_loop.py:85) — only emitted when the tool yields
    at least once, so render stays faithful to the no-yield case."""

    pass


@dataclass
class ToolOutputChunk:
    """One chunk of a tool's streamed output (passthrough)."""

    text: str


@dataclass
class ToolOutputEnd:
    """Output fence-close (agent_loop.py:87)."""

    pass


@dataclass
class RawText:
    """Pass-through rendered text for paths not yet structured (non-verbose mode,
    which uses _clean_content whole-output + compact tool headers). Stage 2
    replaces these with proper structured events."""

    text: str


@dataclass
class TurnEnded:
    """The run loop exited (EXITED / CURRENT_TASK_DONE / MAX_TURNS_EXCEEDED)."""

    exit_reason: dict


def render_event(event, verbose: bool = True) -> str:
    """Default string rendering — byte-for-byte golden for agent_runner_loop's
    current verbose output. Stage 1 validates this against real sessions.

    Non-verbose is carried by RawText passthrough (not yet structured).
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
        return f"🛠️ Tool: `{event.tool_name}`  📥 args:\n````text\n{pretty}\n````\n"
    if isinstance(event, ToolOutputStart):
        return "`````\n"
    if isinstance(event, ToolOutputChunk):
        return event.text
    if isinstance(event, ToolOutputEnd):
        return "`````\n"
    if isinstance(event, RawText):
        return event.text
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
