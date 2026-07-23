from unittest import mock

import pytest

from tau_coding.commands import update


def test_update_requires_uv(monkeypatch):
    monkeypatch.setattr(update.shutil, "which", lambda _: None)
    monkeypatch.setattr(update.os, "chdir", lambda _: None)
    monkeypatch.setattr(
        update.subprocess,
        "run",
        mock.Mock(return_value=mock.Mock(returncode=0, stdout="", stderr="")),
    )

    with pytest.raises(RuntimeError, match="需要 uv"):
        update.run()


def test_update_installs_with_uv(monkeypatch):
    run = mock.Mock(return_value=mock.Mock(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(update.shutil, "which", lambda _: "/usr/bin/uv")
    monkeypatch.setattr(update.os, "chdir", lambda _: None)
    monkeypatch.setattr(update.subprocess, "run", run)

    update.run()

    assert run.call_args_list[-1].args[0] == ["uv", "sync"]
