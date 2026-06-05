from unittest.mock import MagicMock

import slack_off.operations as ops
from slack_off.db import get_workspace
from slack_off.sandbox import PAUSED, RUNNING


def _slack_client(channel_id: str = "C123") -> MagicMock:
    client = MagicMock()
    client.conversations_create.return_value = {"channel": {"id": channel_id}}
    return client


def test_create_workspace_creates_sandbox(monkeypatch):
    monkeypatch.setattr(ops, "create_sandbox", lambda: "sbx_1")

    workspace = ops.create_workspace(_slack_client(), "proj", "U1")

    assert workspace.sandbox_id == "sbx_1"
    assert workspace.sandbox_state == RUNNING


def test_delete_workspace_kills_sandbox(monkeypatch):
    monkeypatch.setattr(ops, "create_sandbox", lambda: "sbx_1")
    killed = []
    monkeypatch.setattr(ops, "kill_sandbox", lambda sid: killed.append(sid))
    client = _slack_client()

    ops.create_workspace(client, "proj", "U1")
    assert ops.delete_workspace(client, "proj", "U1") is True

    assert killed == ["sbx_1"]


def test_pause_is_owner_only(monkeypatch):
    monkeypatch.setattr(ops, "create_sandbox", lambda: "sbx_1")
    paused = []
    monkeypatch.setattr(ops, "pause_sandbox", lambda sid: paused.append(sid))

    ops.create_workspace(_slack_client("C1"), "proj", "U1")

    assert ops.pause_workspace_sandbox("C1", "U2") == "not_owner"
    assert paused == []

    assert ops.pause_workspace_sandbox("C1", "U1") == "paused"
    assert paused == ["sbx_1"]
    assert get_workspace("proj", "U1").sandbox_state == PAUSED


def test_resume_sets_state_running(monkeypatch):
    monkeypatch.setattr(ops, "create_sandbox", lambda: "sbx_1")
    monkeypatch.setattr(ops, "pause_sandbox", lambda sid: None)
    resumed = []
    monkeypatch.setattr(ops, "resume_sandbox", lambda sid: resumed.append(sid))

    ops.create_workspace(_slack_client("C1"), "proj", "U1")
    ops.pause_workspace_sandbox("C1", "U1")

    assert ops.resume_workspace_sandbox("C1", "U1") == "resumed"
    assert resumed == ["sbx_1"]
    assert get_workspace("proj", "U1").sandbox_state == RUNNING


def test_pause_outside_workspace_channel():
    assert ops.pause_workspace_sandbox("C-unknown", "U1") == "not_a_workspace"


def test_resume_outside_workspace_channel():
    assert ops.resume_workspace_sandbox("C-unknown", "U1") == "not_a_workspace"
