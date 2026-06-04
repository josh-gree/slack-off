import pytest

from slack_off.db import get_workspace, save_workspace


def test_save_and_get_workspace():
    save_workspace("my-project", "C123456", "U999")
    workspace = get_workspace("my-project", "U999")

    assert workspace.name == "my-project"
    assert workspace.channel_id == "C123456"
    assert workspace.created_by == "U999"
    assert workspace.is_active is True
    assert workspace.created_at is not None
    assert workspace.modified_at is not None


def test_get_workspace_not_found():
    assert get_workspace("does-not-exist", "U999") is None


def test_duplicate_workspace_name_same_user_raises():
    save_workspace("my-project", "C123456", "U999")
    with pytest.raises(Exception):
        save_workspace("my-project", "C999999", "U999")


def test_duplicate_workspace_name_different_user_allowed():
    save_workspace("my-project", "C123456", "U001")
    save_workspace("my-project", "C999999", "U002")
    assert get_workspace("my-project", "U001").channel_id == "C123456"
    assert get_workspace("my-project", "U002").channel_id == "C999999"
