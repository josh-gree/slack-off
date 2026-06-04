from slack_off.workspace import Workspace


def home_view(workspaces: list[Workspace]) -> dict:
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Welcome to slack-off"}},
        {"type": "divider"},
    ]

    if workspaces:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Your workspaces*"}})
        for w in workspaces:
            blocks.append(_workspace_block(w))
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "You have no active workspaces."},
        })

    blocks.extend([
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "Create Workspace"},
                "action_id": "open_create_modal",
                "style": "primary",
            }],
        },
    ])

    return {"type": "home", "blocks": blocks}


def _workspace_block(w: Workspace) -> dict:
    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{w.name}* — <#{w.channel_id}>"},
        "accessory": {
            "type": "button",
            "text": {"type": "plain_text", "text": "Delete"},
            "action_id": "delete_workspace",
            "value": w.name,
            "style": "danger",
            "confirm": {
                "title": {"type": "plain_text", "text": "Delete workspace"},
                "text": {"type": "mrkdwn", "text": f"Are you sure you want to delete '{w.name}'?"},
                "confirm": {"type": "plain_text", "text": "Delete"},
                "deny": {"type": "plain_text", "text": "Cancel"},
            },
        },
    }


def create_modal_view() -> dict:
    return {
        "type": "modal",
        "callback_id": "create_workspace_modal",
        "title": {"type": "plain_text", "text": "Create Workspace"},
        "submit": {"type": "plain_text", "text": "Create"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [{
            "type": "input",
            "block_id": "workspace_name_block",
            "label": {"type": "plain_text", "text": "Workspace name"},
            "element": {
                "type": "plain_text_input",
                "action_id": "workspace_name",
                "placeholder": {"type": "plain_text", "text": "my-project"},
            },
        }],
    }
