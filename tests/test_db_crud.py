import pytest

from slack_off.db import deactivate_workspace, get_workspace, list_workspaces, save_workspace


def test_list_workspaces_returns_active_only():
    save_workspace("project-a", "C001", "U999")
    save_workspace("project-b", "C002", "U999")
    save_workspace("project-c", "C003", "U999")
    deactivate_workspace("project-b")

    results = list_workspaces("U999")
    names = [r["name"] for r in results]

    assert "project-a" in names
    assert "project-c" in names
    assert "project-b" not in names


def test_list_workspaces_returns_own_only():
    save_workspace("project-a", "C001", "U999")
    save_workspace("project-b", "C002", "U888")

    results = list_workspaces("U999")
    names = [r["name"] for r in results]

    assert "project-a" in names
    assert "project-b" not in names


def test_list_workspaces_empty():
    assert list_workspaces("U999") == []


def test_deactivate_workspace():
    save_workspace("my-project", "C001", "U999")
    deactivate_workspace("my-project")

    workspace = get_workspace("my-project")
    assert workspace["is_active"] == 0


def test_deactivate_updates_modified_at():
    save_workspace("my-project", "C001", "U999")
    before = get_workspace("my-project")["modified_at"]

    import time; time.sleep(1)
    deactivate_workspace("my-project")

    after = get_workspace("my-project")["modified_at"]
    assert after > before
