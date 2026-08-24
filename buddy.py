"""
Buddy pairing: gives each subscriber one accountability partner.
Automatically re-pairs someone if their buddy drops out (leaves/inactive).
"""

import random
import db


def try_pair_user(telegram_id):
    """
    Attempts to pair a user with another unpaired user.
    Returns the buddy's telegram_id if paired, or None if no one else
    is currently available (they'll be paired automatically once someone else joins).
    """
    candidates = db.get_unpaired_users(exclude_telegram_id=telegram_id)
    if not candidates:
        return None

    buddy = random.choice(candidates)
    db.set_buddy_pair(telegram_id, buddy["telegram_id"])
    return buddy["telegram_id"]


def handle_buddy_dropout(dropped_telegram_id):
    """
    Call this when a user leaves/is removed. Frees up their buddy
    so the buddy becomes eligible for automatic re-pairing.
    Returns the freed buddy's telegram_id, or None if they had no buddy.
    """
    user = db.get_user(dropped_telegram_id)
    if not user or not user["buddy_id"]:
        return None

    freed_buddy_id = user["buddy_id"]
    db.clear_buddy(dropped_telegram_id)
    return freed_buddy_id


def run_repairing_sweep():
    """
    Run periodically (e.g. as part of the daily scheduled task) to catch
    anyone left unpaired and try to match them up.
    Returns list of (user_id, buddy_id) pairs newly made.
    """
    unpaired = db.get_unpaired_users()
    new_pairs = []
    pool = unpaired.copy()

    while len(pool) >= 2:
        a = pool.pop()
        b = pool.pop()
        db.set_buddy_pair(a["telegram_id"], b["telegram_id"])
        new_pairs.append((a["telegram_id"], b["telegram_id"]))

    return new_pairs
