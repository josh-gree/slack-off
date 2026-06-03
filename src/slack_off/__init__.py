import logging
import os

from dotenv import load_dotenv
from slack_bolt import App

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"])


@app.message()
def echo(message, say):
    logging.info(f"Received message: {message['text']}")
    say(f"ECHO: {message['text']}")


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
