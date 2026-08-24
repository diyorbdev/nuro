"""
Standalone script for PythonAnywhere's FREE daily Scheduled Task.
Runs the full daily maintenance cycle:
1. Resets any streaks broken by 2+ missed days
2. Re-pairs anyone left without a buddy
3. Posts a translated research paper to the public channel
"""

from app import run_daily_post, run_daily_maintenance

if __name__ == "__main__":
    run_daily_maintenance()
    run_daily_post()
