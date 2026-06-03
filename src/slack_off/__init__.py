import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_sdk.errors import SlackApiError

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

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
                        "text": "Use `/new <name>` here to create a new channel with me already in it.",
                    },
                },
            ],
        },
    )


def create_channel(client, channel_name: str, user_id: str) -> str:
    result = client.conversations_create(name=channel_name, is_private=True)
    channel_id = result["channel"]["id"]
    client.conversations_invite(channel=channel_id, users=user_id)
    return channel_id


@app.command("/new")
def new_channel(ack, respond, command, client):
    ack()

    if command["channel_name"] != "directmessage":
        respond("'/new' can only be used from the App Home.")
        return

    channel_name = command["text"].strip()
    if not channel_name:
        respond("Please provide a channel name: '/new <name>'")
        return

    try:
        channel_id = create_channel(client, channel_name, command["user_id"])
        respond(f"Created private channel <#{channel_id}> and added you to it.")
    except SlackApiError as e:
        if e.response["error"] == "name_taken":
            respond(f"A channel named '{channel_name}' already exists.")
        else:
            raise


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
