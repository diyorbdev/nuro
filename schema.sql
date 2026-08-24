-- Nuro database schema
-- SQLite (works natively on PythonAnywhere free tier, no extra service needed)

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at TEXT NOT NULL,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    last_submission_date TEXT,           -- ISO date (YYYY-MM-DD) of last accepted submission
    buddy_id INTEGER,                     -- telegram_id of paired buddy, NULL if unpaired
    is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS weekly_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start_date TEXT NOT NULL,        -- ISO date of the Monday this challenge started
    fact_text TEXT NOT NULL,
    challenge_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,           -- full ISO timestamp
    submission_date TEXT NOT NULL,        -- ISO date (for streak/day-based logic)
    photo_file_id TEXT NOT NULL,          -- Telegram's file_id for the proof photo
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
    FOREIGN KEY (challenge_id) REFERENCES weekly_challenges(id)
);

-- Prevents someone from submitting twice in the same day counting as two credits
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_submission_per_day
ON submissions(telegram_id, submission_date);

CREATE INDEX IF NOT EXISTS idx_submissions_date ON submissions(submission_date);
