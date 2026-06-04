from slack_off.db import deactivate_workspace, get_workspace, save_workspace
from slack_off.workspace import Workspace


def create_workspace(client, name: str, user_id: str) -> Workspace:
    result = client.conversations_create(name=name, is_private=True)
    channel_id = result["channel"]["id"]
    client.conversations_invite(channel=channel_id, users=user_id)
    return save_workspace(name, channel_id, user_id)


def delete_workspace(client, name: str, user_id: str) -> bool:
    workspace = get_workspace(name, user_id)
    if not workspace or not workspace.is_active:
        return False
    client.conversations_archive(channel=workspace.channel_id)
    deactivate_workspace(name, user_id)
    return True
