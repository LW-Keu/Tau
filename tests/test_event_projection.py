from apps.common.event_projection import last_turn_text
from tau_agent.events import AssistantTextChunk, TurnEnded, TurnStarted


def test_last_turn_running_projects_summary():
    events = [
        TurnStarted(1),
        AssistantTextChunk("<summary>working</summary>\nold"),
        TurnStarted(2),
        AssistantTextChunk("<summary>current</summary>\nnew"),
    ]
    assert last_turn_text(events, running=True) == "current"


def test_last_turn_finished_projects_reply():
    events = [
        TurnStarted(1),
        AssistantTextChunk("<summary>done</summary>\n[Info] hidden\nanswer"),
        TurnEnded({"result": "CURRENT_TASK_DONE"}),
    ]
    assert last_turn_text(events, running=False) == "answer"
