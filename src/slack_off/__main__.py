import logging
import os

from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_off import app

logging.info("Starting bot...")
SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
