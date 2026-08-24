"""
Standalone script for PythonAnywhere's FREE daily Scheduled Task.
This is what actually posts content automatically once a day —
set this script to run once daily in PythonAnywhere's "Tasks" tab (free tier allows one).
"""

from app import run_daily_post

if __name__ == "__main__":
    run_daily_post()
