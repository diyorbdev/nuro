"""
Nuro — full Telegram webhook app.
Handles: account creation, daily photo submissions + streak tracking,
buddy pairing, weekly leaderboard, and admin commands (set challenge, broadcast).

Runs on PythonAnywhere's free tier as a Flask web app (webhook-based,
since free tier can't run a continuous polling process).
"""

import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests as http

load_dotenv()

import db
import buddy
import admin as admin_module
import leaderboard as leaderboard_module
import chronotype
from paper_search import get_daily_paper
from content_generator import build_daily_post

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
db.init_db()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Comma-separated list of telegram user IDs allowed to use admin commands.
# Set this in your .env, e.g. ADMIN_IDS=123456789,987654321
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}


def send_message(chat_id, text, parse_mode="Markdown"):
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    http.post(f"{TELEGRAM_API}/sendMessage", data=payload, timeout=20)


def send_photo(chat_id, photo_file_id, caption=None):
    payload = {"chat_id": chat_id, "photo": photo_file_id}
    if caption:
        payload["caption"] = caption
    http.post(f"{TELEGRAM_API}/sendPhoto", data=payload, timeout=20)


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)

    # Handle inline keyboard button presses (used by the chronotype quiz)
    callback = update.get("callback_query")
    if callback:
        cb_chat_id = callback["message"]["chat"]["id"]
        cb_message_id = callback["message"]["message_id"]
        cb_telegram_id = callback["from"]["id"]
        cb_data = callback.get("data", "")
        http.post(f"{TELEGRAM_API}/answerCallbackQuery", data={"callback_query_id": callback["id"]}, timeout=10)
        if cb_data.startswith("meq:"):
            chronotype.handle_chronotype_callback(cb_chat_id, cb_telegram_id, cb_message_id, cb_data)
        return "ok"

    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    from_user = message.get("from", {})
    telegram_id = from_user.get("id")

    if not chat_id or not telegram_id:
        return "ok"

    text = message.get("text", "") or ""
    photos = message.get("photo")

    # Ensure the user has an account for any interaction
    is_new = db.create_user_if_not_exists(
        telegram_id,
        from_user.get("username"),
        from_user.get("first_name"),
        is_admin=telegram_id in ADMIN_IDS,
    )

    if text.startswith("/start chronotype"):
        if is_new:
            handle_start(chat_id, telegram_id)
        chronotype.start_chronotype_quiz(chat_id, telegram_id)
    elif is_new:
        handle_start(chat_id, telegram_id)
    elif text == "/start":
        handle_start(chat_id, telegram_id, already_registered=True)
    elif text == "/leaderboard":
        send_message(chat_id, leaderboard_module.format_leaderboard_message())
    elif text == "/mystreak":
        handle_mystreak(chat_id, telegram_id)
    elif text == "/challenge":
        handle_show_challenge(chat_id)
    elif text.startswith("/setchallenge"):
        handle_setchallenge(chat_id, telegram_id, text)
    elif text == "/broadcast":
        handle_broadcast(chat_id, telegram_id)
    elif text == "/postnow":
        send_message(chat_id, "Fetching a research paper for the channel...")
        run_daily_post()
        send_message(chat_id, "Done — check the channel.")
    elif text == "/chronotype":
        start_chronotype_quiz(chat_id, telegram_id)
    elif photos:
        handle_photo_submission(chat_id, telegram_id, photos)
    elif text:
        send_message(
            chat_id,
            "I didn't recognize that command. Try /challenge, /mystreak, /leaderboard, "
            "or just send a photo to log today's challenge.",
        )

    return "ok"


def handle_start(chat_id, telegram_id, already_registered=False):
    if already_registered:
        send_message(chat_id, "You're already registered! Send /challenge to see this week's task.")
        return

    send_message(
        chat_id,
        "Welcome to Nuro! 🧠\n\n"
        "Every week you'll get a real neuroscience finding plus a practical challenge "
        "based on it. Submit a photo each day you complete it to build your streak.\n\n"
        "Commands:\n"
        "/challenge — see this week's challenge\n"
        "/mystreak — check your current streak\n"
        "/leaderboard — see this week's top performers\n"
        "/chronotype — take the 19-question sleep-type test\n\n"
        "Let's find you an accountability buddy...",
    )

    buddy_id = buddy.try_pair_user(telegram_id)
    if buddy_id:
        buddy_user = db.get_user(buddy_id)
        buddy_name = buddy_user["first_name"] or buddy_user["username"] or "your buddy"
        send_message(chat_id, f"You've been paired with {buddy_name}! Encourage each other. 🤝")
        send_message(
            buddy_id,
            f"You've got a new accountability buddy: {db.get_user(telegram_id)['first_name'] or 'a new student'}! 🤝",
        )
    else:
        send_message(chat_id, "No one's available to pair with just yet — you'll be matched as soon as someone joins!")

    handle_show_challenge(chat_id)


def handle_show_challenge(chat_id):
    challenge = db.get_current_challenge()
    if not challenge:
        send_message(chat_id, "No challenge has been set yet this week — check back soon!")
        return
    send_message(
        chat_id,
        f"🧠 *This Week's Challenge*\n\n*The Science:*\n{challenge['fact_text']}\n\n"
        f"*Your Task:*\n{challenge['challenge_text']}\n\nSend a photo to log today's proof!",
    )


def handle_mystreak(chat_id, telegram_id):
    user = db.get_user(telegram_id)
    send_message(
        chat_id,
        f"🔥 Current streak: {user['current_streak']} days\n"
        f"🏆 Longest streak: {user['longest_streak']} days",
    )


def handle_photo_submission(chat_id, telegram_id, photos):
    challenge = db.get_current_challenge()
    if not challenge:
        send_message(chat_id, "No active challenge to submit for right now — check back soon!")
        return

    largest_photo = photos[-1]  # Telegram sends multiple sizes; last is highest-res
    new_streak = db.record_submission(telegram_id, challenge["id"], largest_photo["file_id"])

    if new_streak is None:
        send_message(chat_id, "You've already submitted today! See you tomorrow. 💪")
        return

    send_message(chat_id, f"✅ Logged! Your streak is now {new_streak} days. Keep it up!")

    user = db.get_user(telegram_id)
    if user["buddy_id"]:
        buddy_name = user["first_name"] or user["username"] or "Your buddy"
        send_message(user["buddy_id"], f"🎉 {buddy_name} just completed today's challenge!")


def handle_setchallenge(chat_id, telegram_id, text):
    if telegram_id not in ADMIN_IDS:
        send_message(chat_id, "This command is admin-only.")
        return

    args_text = text.replace("/setchallenge", "", 1).strip()
    success, response = admin_module.handle_setchallenge(args_text)
    send_message(chat_id, response)


def handle_broadcast(chat_id, telegram_id):
    if telegram_id not in ADMIN_IDS:
        send_message(chat_id, "This command is admin-only.")
        return

    message = admin_module.build_broadcast_message()
    if not message:
        send_message(chat_id, "No challenge set yet — use /setchallenge first.")
        return

    subscriber_ids = admin_module.get_all_subscriber_ids()
    sent = 0
    for sub_id in subscriber_ids:
        try:
            send_message(sub_id, message)
            sent += 1
        except Exception as e:
            logger.warning(f"Failed to broadcast to {sub_id}: {e}")

    send_message(chat_id, f"✅ Broadcast sent to {sent} subscribers.")


def run_daily_post():
    """Posts a translated research paper to the public channel (separate from the challenge system)."""
    paper = get_daily_paper()
    if paper is None:
        logger.warning("No new paper found today; skipping post.")
        return
    try:
        message = build_daily_post(paper)
        send_message(CHANNEL_ID, message)
        logger.info(f"Posted: {paper['title']}")
    except Exception as e:
        logger.error(f"Failed to post daily content: {e}")


def run_daily_maintenance():
    """Call this once daily via scheduled task, BEFORE the day's activity starts."""
    db.check_and_reset_stale_streaks()
    new_pairs = buddy.run_repairing_sweep()
    for user_id, buddy_id in new_pairs:
        u = db.get_user(user_id)
        b = db.get_user(buddy_id)
        send_message(user_id, f"You've been paired with {b['first_name'] or 'a fellow student'}! 🤝")
        send_message(buddy_id, f"You've been paired with {u['first_name'] or 'a fellow student'}! 🤝")


@app.route("/", methods=["GET"])
def health_check():
    return "Nuro bot webhook is alive."


if __name__ == "__main__":
    app.run()
