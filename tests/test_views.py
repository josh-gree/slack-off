from slack_off.views import create_modal_view, home_view
from slack_off.workspace import Workspace


def _make_workspace(name: str, channel_id: str) -> Workspace:
    return Workspace(
        id=1,
        name=name,
        channel_id=channel_id,
        created_by="U999",
        is_active=True,
        created_at="2026-01-01 00:00:00",
        modified_at="2026-01-01 00:00:00",
    )


def _block_text(block):
    text = block.get("text", {})
    return text.get("text", "") if isinstance(text, dict) else ""


def test_home_view_lists_each_workspace():
    workspaces = [_make_workspace("alpha", "C001"), _make_workspace("beta", "C002")]

    view = home_view(workspaces)
    all_text = " ".join(_block_text(b) for b in view["blocks"])

    assert "alpha" in all_text
    assert "beta" in all_text


def test_home_view_has_delete_button_per_workspace():
    workspaces = [_make_workspace("alpha", "C001"), _make_workspace("beta", "C002")]

    view = home_view(workspaces)
    delete_values = [
        b["accessory"]["value"]
        for b in view["blocks"]
        if b.get("accessory", {}).get("action_id") == "delete_workspace"
    ]

    assert delete_values == ["alpha", "beta"]


def test_home_view_empty_shows_message():
    view = home_view([])
    all_text = " ".join(_block_text(b) for b in view["blocks"])

    assert "no active workspaces" in all_text


def test_home_view_always_has_create_button():
    view = home_view([])
    action_ids = [
        e["action_id"]
        for b in view["blocks"]
        if b.get("type") == "actions"
        for e in b.get("elements", [])
    ]

    assert "open_create_modal" in action_ids


def test_create_modal_view_has_name_input():
    view = create_modal_view()

    assert view["callback_id"] == "create_workspace_modal"
    block_ids = [b.get("block_id") for b in view["blocks"]]
    assert "workspace_name_block" in block_ids
