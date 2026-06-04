import json
from unittest.mock import MagicMock

from slack_off import _publish_home
from slack_off.db import save_workspace


def _get_published_blocks(client):
    call_kwargs = client.views_publish.call_args.kwargs
    return call_kwargs["view"]["blocks"]


def _block_text(block):
    text = block.get("text", {})
    return text.get("text", "") if isinstance(text, dict) else ""


def test_home_shows_workspaces(monkeypatch):
    save_workspace("alpha", "C001", "U999")
    save_workspace("beta", "C002", "U999")

    client = MagicMock()
    _publish_home(client, "U999")

    blocks = _get_published_blocks(client)
    all_text = " ".join(_block_text(b) for b in blocks)

    assert "alpha" in all_text
    assert "beta" in all_text


def test_home_shows_delete_buttons_for_each_workspace():
    save_workspace("alpha", "C001", "U999")
    save_workspace("beta", "C002", "U999")

    client = MagicMock()
    _publish_home(client, "U999")

    blocks = _get_published_blocks(client)
    delete_values = [
        b["accessory"]["value"]
        for b in blocks
        if b.get("accessory", {}).get("action_id") == "delete_workspace"
    ]

    assert "alpha" in delete_values
    assert "beta" in delete_values


def test_home_shows_empty_message_when_no_workspaces():
    client = MagicMock()
    _publish_home(client, "U999")

    blocks = _get_published_blocks(client)
    all_text = " ".join(_block_text(b) for b in blocks)

    assert "no active workspaces" in all_text


def test_home_always_has_create_button():
    client = MagicMock()
    _publish_home(client, "U999")

    blocks = _get_published_blocks(client)
    action_ids = [
        e["action_id"]
        for b in blocks
        if b.get("type") == "actions"
        for e in b.get("elements", [])
    ]

    assert "open_create_modal" in action_ids
