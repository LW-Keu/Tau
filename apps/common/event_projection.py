import re

from tau_agent.events import TurnEnded, TurnStarted, render_event


def event_turns(events, verbose=True):
    turns = []
    current = ""
    for event in events:
        if isinstance(event, TurnStarted):
            if current.strip() or turns:
                turns.append(current)
                current = ""
        elif not isinstance(event, TurnEnded):
            current += render_event(event, verbose)
    turns.append(current)
    return turns


def turn_title(text):
    cleaned = re.sub(
        r"`{3,}.*?`{3,}|<thinking>.*?</thinking>", "", text, flags=re.DOTALL
    )
    summaries = re.findall(
        r"<summary>\s*((?:(?!<summary>).)*?)\s*</summary>",
        cleaned,
        re.DOTALL,
    )
    title = summaries[0].strip().split("\n", 1)[0] if summaries else re.sub(
        r",?\s*args:.*$", "", cleaned.strip().split("\n", 1)[0]
    )
    return title[:72] + "..." if len(title) > 72 else title


def last_turn_text(events, running):
    if not any(isinstance(event, TurnStarted) for event in events):
        return ""
    turns = event_turns(events, verbose=False)
    text = turns[-1].strip() if turns else ""
    if running:
        match = re.search(r"<summary>(.*?)\s*</summary>", text, re.DOTALL)
        summary = match.group(1).strip() if match else ""
        return summary[-1000:]
    text = re.sub(r"<summary>.*?\s*</summary>\s*", "", text, flags=re.DOTALL)
    text = re.sub(r"\[(Status|Info)\][^\n]*\n?", "", text).strip()
    return text[-3000:]
