import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

ROOT = Path(__file__).parent.parent


@pytest.fixture
def bot_process():
    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "slack_off"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        cwd=ROOT,
    )

    connected = threading.Event()

    def watch():
        for line in proc.stderr:
            if "Bolt app is running" in line:
                connected.set()
                break

    threading.Thread(target=watch, daemon=True).start()

    if not connected.wait(timeout=30):
        proc.terminate()
        raise TimeoutError("Bot failed to connect within 30s")

    yield proc

    proc.terminate()
    proc.wait()


@pytest.fixture
def test_user():
    """Client that sends messages as a test user (slack-off-test app)."""
    return WebClient(token=os.environ["SLACK_TEST_TOKEN"])


@pytest.fixture
def bot():
    """Client for the echo bot under test (slack-off app)."""
    return WebClient(token=os.environ["SLACK_BOT_TOKEN"])


def test_echo(bot_process, test_user, bot):
    channel = os.environ["SLACK_TEST_CHANNEL"]
    user_message = f"hello-{uuid.uuid4()}"
    expected_bot_reply = f"ECHO: {user_message}"

    bot_id = bot.auth_test()["bot_id"]

    # User sends a message
    test_user.chat_postMessage(channel=channel, text=user_message)

    # Poll until the bot reply appears or we time out
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        history = bot.conversations_history(channel=channel, limit=10)
        bot_replies = [m["text"] for m in history["messages"] if m.get("bot_id") == bot_id]
        if expected_bot_reply in bot_replies:
            return
        time.sleep(0.5)

    assert False, f"Expected bot reply '{expected_bot_reply}' but bot sent: {bot_replies}"
