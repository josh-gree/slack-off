import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_sdk.errors import SlackApiError

from slack_off.db import deactivate_workspace, get_workspace, init_db, list_workspaces, save_workspace

logging.basicConfig(level=logging.DEBUG)

load_dotenv()
init_db()

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])


def _publish_home(client, user_id: str) -> None:
    workspaces = list_workspaces(user_id)

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Welcome to slack-off"}},
        {"type": "divider"},
    ]

    if workspaces:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Your workspaces*"}})
        for w in workspaces:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{w['name']}* — <#{w['channel_id']}>"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Delete"},
                    "action_id": "delete_workspace",
                    "value": w["name"],
                    "style": "danger",
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Delete workspace"},
                        "text": {"type": "mrkdwn", "text": f"Are you sure you want to delete '{w['name']}'?"},
                        "confirm": {"type": "plain_text", "text": "Delete"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                },
            })
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

    client.views_publish(user_id=user_id, view={"type": "home", "blocks": blocks})


@app.message()
def echo(message, say):
    logging.info(f"Received message: {message['text']}")
    say(f"ECHO: {message['text']}")


@app.event("app_home_opened")
def app_home_opened(client, event):
    _publish_home(client, event["user"])


@app.action("open_create_modal")
def open_create_modal(ack, client, body):
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
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
        },
    )


@app.view("create_workspace_modal")
def handle_create_workspace_modal(ack, body, client):
    user_id = body["user"]["id"]
    workspace_name = body["view"]["state"]["values"]["workspace_name_block"]["workspace_name"]["value"].strip()

    try:
        create_workspace(client, workspace_name, user_id)
    except SlackApiError as e:
        if e.response["error"] == "name_taken":
            ack(response_action="errors", errors={"workspace_name_block": f"A workspace named '{workspace_name}' already exists."})
            return
        raise

    ack()
    _publish_home(client, user_id)


@app.action("delete_workspace")
def handle_delete_workspace(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    workspace_name = body["actions"][0]["value"]

    workspace = get_workspace(workspace_name)
    if workspace and workspace["is_active"]:
        client.conversations_archive(channel=workspace["channel_id"])
        deactivate_workspace(workspace_name)

    _publish_home(client, user_id)


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


@app.command("/list")
def list_workspaces_command(ack, respond, command):
    ack()

    if command["channel_name"] != "directmessage":
        respond("'/list' can only be used from the App Home.")
        return

    workspaces = list_workspaces(command["user_id"])

    if not workspaces:
        respond("You have no active workspaces.")
        return

    lines = [f"- {w['name']} (<#{w['channel_id']}>)" for w in workspaces]
    respond("\n".join(lines))


@app.command("/delete")
def delete_workspace_command(ack, respond, command, client):
    ack()

    if command["channel_name"] != "directmessage":
        respond("'/delete' can only be used from the App Home.")
        return

    workspace_name = command["text"].strip()
    if not workspace_name:
        respond("Please provide a workspace name: '/delete <name>'")
        return

    workspace = get_workspace(workspace_name)

    if not workspace or not workspace["is_active"]:
        respond(f"No active workspace named '{workspace_name}' found.")
        return

    if workspace["created_by"] != command["user_id"]:
        respond("You can only delete workspaces you created.")
        return

    client.conversations_archive(channel=workspace["channel_id"])
    deactivate_workspace(workspace_name)
    respond(f"Workspace '{workspace_name}' has been deleted.")
