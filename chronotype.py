"""
Interactive Morningness-Eveningness Questionnaire (MEQ), Horne & Ostberg (1976),
self-assessment version. Delivered as a button-based quiz inside Telegram via
inline keyboards, one question at a time, with automatic scoring at the end.

Shared with Nuro by Dr. Ju Lynn Ong (NUS) as a tool for understanding whether
a person is biologically a "morning type," "evening type," or in between.
"""

import os
import requests as http

BOT_TOKEN = None
TELEGRAM_API = None


def _ensure_token():
    """Lazily reads the bot token so import order relative to load_dotenv() doesn't matter."""
    global BOT_TOKEN, TELEGRAM_API
    if BOT_TOKEN is None:
        BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
        TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# In-memory session state: {telegram_id: {"q": current_index, "score": running_total}}
# Fine for a small/medium user base on a single-process free-tier host.
SESSIONS = {}

# Each question: (text, [(label, points), ...])
QUESTIONS = [
    ("1/19. What time would you get up if you were entirely free to plan your day?",
     [("5:00-6:30 AM", 5), ("6:30-7:45 AM", 4), ("7:45-9:45 AM", 3), ("9:45-11:00 AM", 2), ("11:00 AM-12 noon", 1)]),
    ("2/19. What time would you go to bed if you were entirely free to plan your evening?",
     [("8:00-9:00 PM", 5), ("9:00-10:15 PM", 4), ("10:15 PM-12:30 AM", 3), ("12:30-1:45 AM", 2), ("1:45-3:00 AM", 1)]),
    ("3/19. If you must get up at a specific time, how much do you depend on an alarm clock?",
     [("Not at all", 4), ("Slightly", 3), ("Somewhat", 2), ("Very much", 1)]),
    ("4/19. How easy do you find it to get up in the morning (normally)?",
     [("Very difficult", 1), ("Somewhat difficult", 2), ("Fairly easy", 3), ("Very easy", 4)]),
    ("5/19. How alert do you feel during the first half hour after waking?",
     [("Not at all alert", 1), ("Slightly alert", 2), ("Fairly alert", 3), ("Very alert", 4)]),
    ("6/19. How hungry do you feel during the first half hour after waking?",
     [("Not at all hungry", 1), ("Slightly hungry", 2), ("Fairly hungry", 3), ("Very hungry", 4)]),
    ("7/19. During the first half hour after waking, how tired do you feel?",
     [("Very tired", 1), ("Fairly tired", 2), ("Fairly refreshed", 3), ("Very refreshed", 4)]),
    ("8/19. With no commitments the next day, when would you go to bed vs. usual?",
     [("Seldom/never later", 4), ("Less than 1h later", 3), ("1-2h later", 2), ("More than 2h later", 1)]),
    ("9/19. Exercising 7-8 AM based only on your internal clock, how would you perform?",
     [("Good form", 4), ("Reasonable form", 3), ("Difficult", 2), ("Very difficult", 1)]),
    ("10/19. What time in the evening do you start feeling tired / need sleep?",
     [("8:00-9:00 PM", 5), ("9:00-10:15 PM", 4), ("10:15 PM-12:45 AM", 3), ("12:45-2:00 AM", 2), ("2:00-3:00 AM", 1)]),
    ("11/19. For peak performance on a 2-hour mentally exhausting test, best time?",
     [("8-10 AM", 6), ("11 AM-1 PM", 4), ("3-5 PM", 2), ("7-9 PM", 0)]),
    ("12/19. If you got into bed at 11 PM, how tired would you be?",
     [("Not at all tired", 0), ("A little tired", 2), ("Fairly tired", 3), ("Very tired", 5)]),
    ("13/19. Woke up several hours later than usual with no commitments — most likely?",
     [("Wake at usual time, stay awake", 4), ("Wake at usual time, doze after", 3), ("Wake at usual time, fall back asleep", 2), ("Wake later than usual", 1)]),
    ("14/19. Night watch 4-6 AM, no commitments next day — best option?",
     [("Stay up until watch is over", 1), ("Nap before, sleep after", 2), ("Sleep well before, nap after", 3), ("Sleep only before the watch", 4)]),
    ("15/19. 2 hours of hard physical work, free to choose — best time (internal clock only)?",
     [("8-10 AM", 4), ("11 AM-1 PM", 3), ("3-5 PM", 2), ("7-9 PM", 1)]),
    ("16/19. Exercising 10-11 PM based only on your internal clock, how would you perform?",
     [("Good form", 1), ("Reasonable form", 2), ("Difficult", 3), ("Very difficult", 4)]),
    ("17/19. Choosing your own 5-hour interesting, performance-paid workday — start time?",
     [("4-8 AM", 5), ("8-9 AM", 4), ("9 AM-2 PM", 3), ("2-5 PM", 2), ("5 PM-4 AM", 1)]),
    ("18/19. What time of day do you usually feel your best?",
     [("5-8 AM", 5), ("8-10 AM", 4), ("10 AM-5 PM", 3), ("5-10 PM", 2), ("10 PM-5 AM", 1)]),
    ("19/19. Which type do you consider yourself?",
     [("Definitely morning type", 6), ("More morning than evening", 4), ("More evening than morning", 2), ("Definitely evening type", 1)]),
]


def _send(chat_id, text, reply_markup=None):
    _ensure_token()
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    http.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=20)


def _edit(chat_id, message_id, text, reply_markup=None):
    _ensure_token()
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    http.post(f"{TELEGRAM_API}/editMessageText", json=payload, timeout=20)


def _keyboard_for(question_index):
    _, options = QUESTIONS[question_index]
    buttons = [[{"text": label, "callback_data": f"meq:{question_index}:{points}"}] for label, points in options]
    return {"inline_keyboard": buttons}


def start_chronotype_quiz(chat_id, telegram_id):
    SESSIONS[telegram_id] = {"q": 0, "score": 0}
    _send(
        chat_id,
        "🧬 Chronotype Test (Morningness-Eveningness Questionnaire)\n\n"
        "19 quick questions. Answer honestly, based on how you actually feel — "
        "not how you think you should feel. Tap a button to answer.\n\n"
        "Source: Horne & Ostberg (1976), shared with Nuro by Dr. Ju Lynn Ong (NUS).",
    )
    q_text, _ = QUESTIONS[0]
    _send(chat_id, q_text, reply_markup=_keyboard_for(0))


def handle_chronotype_callback(chat_id, telegram_id, message_id, data):
    """
    data format: "meq:<question_index>:<points>"
    Only processes if it matches the user's current expected question,
    to avoid double-counting from stale button presses.
    """
    try:
        _, q_idx_str, points_str = data.split(":")
        q_idx = int(q_idx_str)
        points = int(points_str)
    except (ValueError, IndexError):
        return

    session = SESSIONS.get(telegram_id)
    if not session or session["q"] != q_idx:
        return  # stale or out-of-order tap; ignore

    session["score"] += points
    session["q"] += 1

    if session["q"] < len(QUESTIONS):
        q_text, _ = QUESTIONS[session["q"]]
        _edit(chat_id, message_id, q_text, reply_markup=_keyboard_for(session["q"]))
    else:
        _finish_quiz(chat_id, telegram_id, message_id, session["score"])


def _finish_quiz(chat_id, telegram_id, message_id, score):
    if score <= 30:
        label, emoji = "Definite evening type 🦉", "🦉"
    elif score <= 41:
        label, emoji = "Moderate evening type 🌙", "🌙"
    elif score <= 58:
        label, emoji = "Intermediate type ⚖️", "⚖️"
    elif score <= 69:
        label, emoji = "Moderate morning type 🌤️", "🌤️"
    else:
        label, emoji = "Definite morning type ☀️", "☀️"

    _edit(
        chat_id, message_id,
        f"✅ Done! Your score: {score}/86\n\n{emoji} {label}\n\n"
        "This is a real, validated instrument (not a fun quiz) — it reflects your "
        "biological chronotype, not discipline or laziness. A sleep schedule that "
        "fights your natural type is much harder to sustain long-term.\n\n"
        "Send /challenge to see how this connects to this week's sleep challenge.",
    )
    SESSIONS.pop(telegram_id, None)
