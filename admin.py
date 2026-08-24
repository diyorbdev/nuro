"""
Admin-only commands: setting the weekly fact + challenge, and broadcasting
messages to every subscriber. Only telegram_ids marked is_admin=1 in the
database can use these.
"""

import db


def handle_setchallenge(args_text):
    """
    Parses admin input in the format:
    FACT: <the scientific fact>
    CHALLENGE: <the practical challenge>

    Returns (success: bool, message: str)
    """
    if "FACT:" not in args_text or "CHALLENGE:" not in args_text:
        return False, (
            "Format must be:\n\nFACT: <the scientific fact>\nCHALLENGE: <the practical task>\n\n"
            "Example:\nFACT: Sleep under 6.5h significantly hurts memory consolidation.\n"
            "CHALLENGE: Get 7+ hours of sleep tonight and log your bedtime."
        )

    try:
        fact_part = args_text.split("FACT:")[1].split("CHALLENGE:")[0].strip()
        challenge_part = args_text.split("CHALLENGE:")[1].strip()
    except IndexError:
        return False, "Couldn't parse that format. Use FACT: ... and CHALLENGE: ... on separate lines."

    if not fact_part or not challenge_part:
        return False, "Both FACT and CHALLENGE need content."

    challenge_id = db.create_weekly_challenge(fact_part, challenge_part)
    return True, f"✅ New weekly challenge #{challenge_id} created. Ready to broadcast with /broadcast."


def build_broadcast_message():
    """Builds the message that goes out to every subscriber for the current challenge."""
    challenge = db.get_current_challenge()
    if not challenge:
        return None

    return (
        f"🧠 *This Week's Nuro Challenge*\n\n"
        f"*The Science:*\n{challenge['fact_text']}\n\n"
        f"*Your Challenge:*\n{challenge['challenge_text']}\n\n"
        f"Submit a photo proof each day you complete it. "
        f"Missing one day won't break your streak — missing two in a row will, so stay consistent! 💪"
    )


def get_all_subscriber_ids():
    """Returns telegram_ids of every user, for the broadcast loop."""
    return [u["telegram_id"] for u in db.get_all_users()]
