import pytest

from slack_off.db import deactivate_workspace, get_workspace, list_workspaces, save_workspace


def test_list_workspaces_returns_active_only():
    save_workspace("project-a", "C001", "U999")
    save_workspace("project-b", "C002", "U999")
    save_workspace("project-c", "C003", "U999")
    deactivate_workspace("project-b", "U999")

    results = list_workspaces("U999")
    names = [r.name for r in results]

    assert "project-a" in names
    assert "project-c" in names
    assert "project-b" not in names


def test_list_workspaces_returns_own_only():
    save_workspace("project-a", "C001", "U999")
    save_workspace("project-b", "C002", "U888")

    results = list_workspaces("U999")
    names = [r.name for r in results]

    assert "project-a" in names
    assert "project-b" not in names


def test_list_workspaces_empty():
    assert list_workspaces("U999") == []


def test_deactivate_workspace():
    save_workspace("my-project", "C001", "U999")
    deactivate_workspace("my-project", "U999")

    workspace = get_workspace("my-project", "U999")
    assert workspace.is_active is False


def test_deactivate_updates_modified_at():
    save_workspace("my-project", "C001", "U999")
    before = get_workspace("my-project", "U999").modified_at

    import time; time.sleep(1)
    deactivate_workspace("my-project", "U999")

    after = get_workspace("my-project", "U999").modified_at
    assert after > before


def test_get_workspace_is_user_scoped():
    save_workspace("shared-name", "C001", "U001")
    save_workspace("shared-name", "C002", "U002")

    assert get_workspace("shared-name", "U001").channel_id == "C001"
    assert get_workspace("shared-name", "U002").channel_id == "C002"
    assert get_workspace("shared-name", "U003") is None
