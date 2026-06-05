import logging
from typing import Optional

from slack_off.db import (
    deactivate_workspace,
    get_workspace,
    get_workspace_by_channel,
    save_workspace,
    set_sandbox_state,
)
from slack_off.sandbox import (
    PAUSED,
    RUNNING,
    create_sandbox,
    kill_sandbox,
    pause_sandbox,
    resume_sandbox,
)
from slack_off.workspace import Workspace

logger = logging.getLogger(__name__)


def create_workspace(client, name: str, user_id: str) -> Workspace:
    # Create the sandbox first: it's the most failure-prone step (auth, e2b
    # availability). Doing it before creating the Slack channel means a failure
    # here leaves nothing to clean up, rather than orphaning a channel whose name
    # then stays reserved on Slack.
    sandbox_id = create_sandbox()

    channel_id = None
    try:
        result = client.conversations_create(name=name, is_private=True)
        channel_id = result["channel"]["id"]
        client.conversations_invite(channel=channel_id, users=user_id)
        return save_workspace(
            name, channel_id, user_id, sandbox_id=sandbox_id, sandbox_state=RUNNING
        )
    except Exception:
        # Roll back so we don't leak a sandbox (or an orphaned channel) when a
        # later step fails (e.g. name_taken, invite error).
        if channel_id is not None:
            try:
                client.conversations_archive(channel=channel_id)
            except Exception:
                logger.warning("Failed to archive channel %s during rollback", channel_id)
        try:
            kill_sandbox(sandbox_id)
        except Exception:
            logger.warning("Failed to kill sandbox %s during rollback", sandbox_id)
        raise


def delete_workspace(client, name: str, user_id: str) -> bool:
    workspace = get_workspace(name, user_id)
    if not workspace or not workspace.is_active:
        return False
    client.conversations_archive(channel=workspace.channel_id)
    if workspace.sandbox_id:
        kill_sandbox(workspace.sandbox_id)
    deactivate_workspace(name, user_id)
    return True


def _resolve_owned_workspace(channel_id: str, user_id: str) -> tuple[Optional[Workspace], Optional[str]]:
    """Resolve the active workspace for a channel, enforcing owner-only access.

    Returns (workspace, None) on success, or (None, reason) where reason is one of
    'not_a_workspace' or 'not_owner'.
    """
    workspace = get_workspace_by_channel(channel_id)
    if not workspace:
        return None, "not_a_workspace"
    if workspace.created_by != user_id:
        return None, "not_owner"
    return workspace, None


def pause_workspace_sandbox(channel_id: str, user_id: str) -> str:
    """Pause the sandbox for a workspace channel. Owner-only.

    Returns a status string: 'paused', 'not_a_workspace', 'not_owner', or 'no_sandbox'.
    """
    workspace, reason = _resolve_owned_workspace(channel_id, user_id)
    if reason:
        return reason
    if not workspace.sandbox_id:
        return "no_sandbox"
    pause_sandbox(workspace.sandbox_id)
    set_sandbox_state(workspace.id, PAUSED)
    return "paused"


def resume_workspace_sandbox(channel_id: str, user_id: str) -> str:
    """Resume the sandbox for a workspace channel. Owner-only.

    Returns a status string: 'resumed', 'not_a_workspace', 'not_owner', or 'no_sandbox'.
    """
    workspace, reason = _resolve_owned_workspace(channel_id, user_id)
    if reason:
        return reason
    if not workspace.sandbox_id:
        return "no_sandbox"
    resume_sandbox(workspace.sandbox_id)
    set_sandbox_state(workspace.id, RUNNING)
    return "resumed"
