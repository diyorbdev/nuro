"""
Flask webhook app for the Nuro bot — designed for PythonAnywhere's FREE tier.
Free tier can't run a continuous background process, but it CAN run a
free always-available web app, so Telegram sends commands here via webhook
instead of the bot polling for them.

After deploying, you must tell Telegram where this webhook is (one-time setup,
instructions in README.md).
"""

import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests as http

from paper_search import get_daily_paper
from content_generator import build_daily_post

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    http.post(f"{TELEGRAM_API}/sendMessage", data=payload, timeout=20)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Telegram calls this URL whenever someone messages the bot."""
    update = request.get_json(force=True)
    message = update.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return "ok"

    if text == "/start":
        send_message(
            chat_id,
            "Nuro bot is running. It posts automatically every day.\n"
            "Send /postnow to trigger a post immediately (for testing).",
        )
    elif text == "/postnow":
        send_message(chat_id, "Fetching a paper and building today's post...")
        run_daily_post()
        send_message(chat_id, "Done — check the channel.")

    return "ok"


def run_daily_post():
    """The core job: find a paper, generate content, post it to the channel."""
    paper = get_daily_paper()
    if paper is None:
        logger.warning("No new paper found today; skipping post.")
        return
    try:
        message = build_daily_post(paper)
        send_message(CHANNEL_ID, message, parse_mode="Markdown")
        logger.info(f"Posted: {paper['title']}")
    except Exception as e:
        logger.error(f"Failed to post daily content: {e}")


@app.route("/", methods=["GET"])
def health_check():
    return "Nuro bot webhook is alive."


if __name__ == "__main__":
    app.run()
