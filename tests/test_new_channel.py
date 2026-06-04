import os
import uuid

import pytest
from dotenv import load_dotenv
from slack_sdk import WebClient

from slack_off.operations import create_workspace

load_dotenv()


@pytest.fixture
def bot():
    """Client for the slack-off bot (creates workspaces)."""
    return WebClient(token=os.environ["SLACK_BOT_TOKEN"])


@pytest.fixture
def test_client():
    """The slack-off-test bot — stands in for the user who invokes /new, and inspects/cleans up."""
    return WebClient(token=os.environ["SLACK_TEST_TOKEN"])


def test_create_workspace(bot, test_client):
    workspace_name = f"test-{uuid.uuid4().hex[:8]}"
    channel_id = None

    test_user_id = test_client.auth_test()["user_id"]
    bot_user_id = bot.auth_test()["user_id"]

    try:
        workspace = create_workspace(bot, workspace_name, test_user_id)
        channel_id = workspace.channel_id

        info = test_client.conversations_info(channel=channel_id)["channel"]
        assert info["is_private"], "Workspace channel should be private"

        members = test_client.conversations_members(channel=channel_id)["members"]
        assert bot_user_id in members, "Bot should be a member"
        assert test_user_id in members, "Requesting user should be a member"

    finally:
        if channel_id:
            test_client.conversations_archive(channel=channel_id)
