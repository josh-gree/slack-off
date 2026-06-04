import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_sdk.errors import SlackApiError

from slack_off.db import init_db, save_workspace

logging.basicConfig(level=logging.DEBUG)

load_dotenv()
init_db()

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])


@app.message()
def echo(message, say):
    logging.info(f"Received message: {message['text']}")
    say(f"ECHO: {message['text']}")


@app.event("app_home_opened")
def app_home_opened(client, event):
    client.views_publish(
        user_id=event["user"],
        view={
            "type": "home",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Welcome to slack-off"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Use `/new <name>` here to create a new workspace with me already in it.",
                    },
                },
            ],
        },
    )


def create_workspace(client, workspace_name: str, user_id: str) -> str:
    result = client.conversations_create(name=workspace_name, is_private=True)
    channel_id = result["channel"]["id"]
    client.conversations_invite(channel=channel_id, users=user_id)
    save_workspace(workspace_name, channel_id, user_id)
    return channel_id


@app.command("/new")
def new_workspace(ack, respond, command, client):
    ack()

    if command["channel_name"] != "directmessage":
        respond("'/new' can only be used from the App Home.")
        return

    workspace_name = command["text"].strip()
    if not workspace_name:
        respond("Please provide a workspace name: '/new <name>'")
        return

    try:
        channel_id = create_workspace(client, workspace_name, command["user_id"])
        respond(f"Created workspace <#{channel_id}> and added you to it.")
    except SlackApiError as e:
        if e.response["error"] == "name_taken":
            respond(f"A workspace named '{workspace_name}' already exists.")
        else:
            raise
