import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_sdk.errors import SlackApiError

from slack_off import views
from slack_off.db import init_db, list_workspaces
from slack_off.operations import (
    create_workspace,
    delete_workspace,
    pause_workspace_sandbox,
    resume_workspace_sandbox,
)

logging.basicConfig(level=logging.DEBUG)

load_dotenv()
init_db()

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])


def _publish_home(client, user_id: str) -> None:
    client.views_publish(user_id=user_id, view=views.home_view(list_workspaces(user_id)))


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
    client.views_open(trigger_id=body["trigger_id"], view=views.create_modal_view())


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
    except Exception:
        logging.exception("Failed to create workspace '%s'", workspace_name)
        ack(response_action="errors", errors={"workspace_name_block": "Could not create the workspace's sandbox. Please try again later."})
        return

    ack()
    _publish_home(client, user_id)


@app.action("delete_workspace")
def handle_delete_workspace(ack, body, client):
    ack()
    user_id = body["user"]["id"]
    workspace_name = body["actions"][0]["value"]
    delete_workspace(client, workspace_name, user_id)
    _publish_home(client, user_id)


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
        workspace = create_workspace(client, workspace_name, command["user_id"])
        respond(f"Created workspace <#{workspace.channel_id}> and added you to it.")
    except SlackApiError as e:
        if e.response["error"] == "name_taken":
            respond(f"A workspace named '{workspace_name}' already exists.")
        else:
            raise
    except Exception:
        logging.exception("Failed to create workspace '%s'", workspace_name)
        respond("Could not create the workspace's sandbox. Please try again later.")


_PAUSE_MESSAGES = {
    "paused": "Sandbox paused.",
    "not_a_workspace": "'/pause' can only be used from within a workspace channel.",
    "not_owner": "Only the workspace owner can pause the sandbox.",
    "no_sandbox": "This workspace has no sandbox.",
}

_RESUME_MESSAGES = {
    "resumed": "Sandbox resumed.",
    "not_a_workspace": "'/resume' can only be used from within a workspace channel.",
    "not_owner": "Only the workspace owner can resume the sandbox.",
    "no_sandbox": "This workspace has no sandbox.",
}


@app.command("/pause")
def pause_sandbox_command(ack, respond, command):
    ack()
    result = pause_workspace_sandbox(command["channel_id"], command["user_id"])
    respond(_PAUSE_MESSAGES[result])


@app.command("/resume")
def resume_sandbox_command(ack, respond, command):
    ack()
    result = resume_workspace_sandbox(command["channel_id"], command["user_id"])
    respond(_RESUME_MESSAGES[result])


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

    lines = [f"- {w.name} (<#{w.channel_id}>)" for w in workspaces]
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

    if not delete_workspace(client, workspace_name, command["user_id"]):
        respond(f"No active workspace named '{workspace_name}' found.")
        return

    respond(f"Workspace '{workspace_name}' has been deleted.")
