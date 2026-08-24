"""
Database access layer for Nuro. Uses SQLite (a single file, no extra
service needed - works fine on PythonAnywhere's free tier).
"""

import sqlite3
import os
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "nuro.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Creates all tables if they don't exist yet. Safe to call every startup."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        schema = f.read()
    conn = get_connection()
    conn.executescript(schema)
    conn.commit()
    conn.close()


# ---------- Users ----------

def create_user_if_not_exists(telegram_id, username, first_name, is_admin=False):
    conn = get_connection()
    existing = conn.execute(
        "SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    if existing is None:
        conn.execute(
            """INSERT INTO users (telegram_id, username, first_name, joined_at, is_admin)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_id, username, first_name, datetime.utcnow().isoformat(), int(is_admin)),
        )
        conn.commit()
    conn.close()
    return existing is None  # True if this was a brand-new account


def get_user(telegram_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def is_admin(telegram_id):
    user = get_user(telegram_id)
    return bool(user and user["is_admin"])


def get_all_users():
    conn = get_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return [dict(u) for u in users]


# ---------- Streaks & Submissions ----------

def record_submission(telegram_id, challenge_id, photo_file_id):
    """
    Records a submission and updates the user's streak using the soft-fail rule:
    - Submitting today after a 1-day gap (yesterday missed) still continues the streak.
    - Submitting today after a 2+ day gap resets the streak to 1.
    - Only one submission counted per day (duplicate same-day submissions are ignored).
    Returns the updated streak count, or None if already submitted today.
    """
    today = date.today().isoformat()
    conn = get_connection()

    already_today = conn.execute(
        "SELECT id FROM submissions WHERE telegram_id = ? AND submission_date = ?",
        (telegram_id, today),
    ).fetchone()
    if already_today:
        conn.close()
        return None

    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    last_date_str = user["last_submission_date"]
    current_streak = user["current_streak"]
    longest_streak = user["longest_streak"]

    if last_date_str is None:
        new_streak = 1
    else:
        last_date = date.fromisoformat(last_date_str)
        gap_days = (date.today() - last_date).days
        if gap_days <= 2:
            # 1 day gap = one missed day, forgiven (soft-fail rule)
            new_streak = current_streak + 1
        else:
            # 2+ consecutive missed days = streak resets
            new_streak = 1

    new_longest = max(longest_streak, new_streak)

    conn.execute(
        """INSERT INTO submissions (telegram_id, challenge_id, submitted_at, submission_date, photo_file_id)
           VALUES (?, ?, ?, ?, ?)""",
        (telegram_id, challenge_id, datetime.utcnow().isoformat(), today, photo_file_id),
    )
    conn.execute(
        """UPDATE users SET current_streak = ?, longest_streak = ?, last_submission_date = ?
           WHERE telegram_id = ?""",
        (new_streak, new_longest, today, telegram_id),
    )
    conn.commit()
    conn.close()
    return new_streak


def check_and_reset_stale_streaks():
    """
    Run this once daily (via scheduled task) BEFORE the new day's submissions come in.
    Resets any user's streak to 0 if they've now missed 2+ consecutive days
    (i.e. last submission was 3+ days ago from today).
    """
    conn = get_connection()
    users = conn.execute(
        "SELECT telegram_id, last_submission_date, current_streak FROM users"
    ).fetchall()
    today = date.today()
    for u in users:
        if u["last_submission_date"] is None or u["current_streak"] == 0:
            continue
        last_date = date.fromisoformat(u["last_submission_date"])
        gap_days = (today - last_date).days
        if gap_days >= 3:
            conn.execute(
                "UPDATE users SET current_streak = 0 WHERE telegram_id = ?",
                (u["telegram_id"],),
            )
    conn.commit()
    conn.close()


# ---------- Weekly Challenges ----------

def create_weekly_challenge(fact_text, challenge_text):
    conn = get_connection()
    week_start = date.today().isoformat()
    cur = conn.execute(
        """INSERT INTO weekly_challenges (week_start_date, fact_text, challenge_text, created_at)
           VALUES (?, ?, ?, ?)""",
        (week_start, fact_text, challenge_text, datetime.utcnow().isoformat()),
    )
    conn.commit()
    challenge_id = cur.lastrowid
    conn.close()
    return challenge_id


def get_current_challenge():
    conn = get_connection()
    challenge = conn.execute(
        "SELECT * FROM weekly_challenges ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(challenge) if challenge else None


# ---------- Leaderboard ----------

def get_weekly_leaderboard(limit=10):
    """
    Top N users by number of submissions in the last 7 days.
    Only shows top performers - never exposes who's falling behind.
    """
    conn = get_connection()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    rows = conn.execute(
        """
        SELECT u.telegram_id, u.username, u.first_name, u.current_streak,
               COUNT(s.id) as submissions_this_week
        FROM users u
        JOIN submissions s ON s.telegram_id = u.telegram_id
        WHERE s.submission_date >= ?
        GROUP BY u.telegram_id
        ORDER BY submissions_this_week DESC, u.current_streak DESC
        LIMIT ?
        """,
        (week_ago, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Buddy Pairing ----------

def get_unpaired_users(exclude_telegram_id=None):
    conn = get_connection()
    query = "SELECT * FROM users WHERE buddy_id IS NULL"
    params = ()
    if exclude_telegram_id:
        query += " AND telegram_id != ?"
        params = (exclude_telegram_id,)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_buddy_pair(telegram_id_a, telegram_id_b):
    conn = get_connection()
    conn.execute("UPDATE users SET buddy_id = ? WHERE telegram_id = ?", (telegram_id_b, telegram_id_a))
    conn.execute("UPDATE users SET buddy_id = ? WHERE telegram_id = ?", (telegram_id_a, telegram_id_b))
    conn.commit()
    conn.close()


def clear_buddy(telegram_id):
    """Unpairs a user (e.g. when their buddy drops out), leaving them ready for re-pairing."""
    conn = get_connection()
    user = conn.execute("SELECT buddy_id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    if user and user["buddy_id"]:
        old_buddy_id = user["buddy_id"]
        conn.execute("UPDATE users SET buddy_id = NULL WHERE telegram_id = ?", (telegram_id,))
        conn.execute("UPDATE users SET buddy_id = NULL WHERE telegram_id = ?", (old_buddy_id,))
        conn.commit()
    conn.close()
