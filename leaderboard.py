"""
Weekly leaderboard: shows only the top 10 performers.
Deliberately never shows or ranks who's falling behind, to avoid shame-driven dropout.
"""

import db


def format_leaderboard_message():
    top = db.get_weekly_leaderboard(limit=10)

    if not top:
        return "No submissions yet this week — be the first! 🚀"

    lines = ["🏆 *This Week's Top Performers*\n"]
    medals = ["🥇", "🥈", "🥉"]

    for i, entry in enumerate(top):
        name = entry["first_name"] or entry["username"] or "Student"
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(
            f"{medal} {name} — {entry['submissions_this_week']} days this week "
            f"(🔥 {entry['current_streak']} day streak)"
        )

    lines.append("\nKeep going — next week's board is a fresh start for everyone!")
    return "\n".join(lines)
