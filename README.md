# Nuro Bot — Free Deployment on PythonAnywhere

## What this does
Every day, automatically:
1. Finds a new, relevant research paper (sleep, memory, focus, procrastination, etc.)
2. Translates it into simple, plain English for your audience
3. Generates one concrete task from it
4. Posts it to your Telegram channel

`/start` and `/postnow` also work as live commands via webhook.

## What you need
1. Telegram bot token (from @BotFather) — already have this
2. Anthropic API key (console.anthropic.com) — needs small billing credit
3. A free PythonAnywhere account (no card needed): https://www.pythonanywhere.com/registration/register/beginner/

## Setup on PythonAnywhere (one time, ~15 min)

1. **Upload the code**
   - In PythonAnywhere, open a **Bash console**
   - Run: `git clone https://github.com/diyorbdev/nuro.git`

2. **Install dependencies**
   ```
   cd nuro
   pip install --user -r requirements.txt
   ```

3. **Set your secrets**
   - Copy `.env.example` to `.env`: `cp .env.example .env`
   - Edit it (`nano .env`) and fill in your real `TELEGRAM_BOT_TOKEN`,
     `TELEGRAM_CHANNEL_ID` (`@nurobrain`), and `ANTHROPIC_API_KEY`

4. **Create the free Web App**
   - Go to the **Web** tab → **Add a new web app**
   - Choose **Flask**, Python 3.10
   - Set the source code path to `/home/YOURUSERNAME/nuro`
   - Set the WSGI file to point at `app.py`'s `app` object (PythonAnywhere gives
     you a template file — replace its content to import `app` from `app.py`)
   - Click **Reload** on the Web tab

5. **Tell Telegram where your webhook is** (one-time)
   Run this in a Bash console, replacing YOURUSERNAME and your real token:
   ```
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://YOURUSERNAME.pythonanywhere.com/webhook"
   ```
   You should see `"ok":true` in the response.

6. **Set up the free daily task**
   - Go to the **Tasks** tab → create a new scheduled task
   - Command: `python3.10 /home/YOURUSERNAME/nuro/daily_post.py`
   - Set the time you want it to post daily

7. **Test it**
   - Message your bot `/start` on Telegram — you should get an instant reply
   - Message `/postnow` — check your channel for the post

## Keeping it alive
Free PythonAnywhere web apps need you to log in and click "Run until 3 months
from today" on the Web tab every 3 months, or the app goes offline. Takes 5 seconds.

## Files
- `app.py` — Flask webhook app (handles /start, /postnow, live on PythonAnywhere)
- `daily_post.py` — script triggered by PythonAnywhere's free daily scheduled task
- `paper_search.py` — finds new papers (rotates topics, avoids repeats)
- `content_generator.py` — Claude-powered translation + task generation
- `main.py` — alternate version for continuous hosting (Railway/etc.) if you ever upgrade
- `requirements.txt` — dependencies
- `.env.example` — template for your secrets (rename to `.env`, fill in, never share)
