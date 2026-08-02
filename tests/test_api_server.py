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
