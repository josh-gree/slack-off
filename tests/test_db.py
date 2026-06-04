import pytest

from slack_off.db import get_workspace, save_workspace


def test_save_and_get_workspace():
    save_workspace("my-project", "C123456", "U999")
    row = get_workspace("my-project", "U999")

    assert row["name"] == "my-project"
    assert row["channel_id"] == "C123456"
    assert row["created_by"] == "U999"
    assert row["is_active"] == 1
    assert row["created_at"] is not None
    assert row["modified_at"] is not None


def test_get_workspace_not_found():
    assert get_workspace("does-not-exist", "U999") is None


def test_duplicate_workspace_name_same_user_raises():
    save_workspace("my-project", "C123456", "U999")
    with pytest.raises(Exception):
        save_workspace("my-project", "C999999", "U999")


def test_duplicate_workspace_name_different_user_allowed():
    save_workspace("my-project", "C123456", "U001")
    save_workspace("my-project", "C999999", "U002")
    assert get_workspace("my-project", "U001")["channel_id"] == "C123456"
    assert get_workspace("my-project", "U002")["channel_id"] == "C999999"
