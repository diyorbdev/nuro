# Nuro Bot — Setup Guide

## What this does
Every day, automatically:
1. Finds a new, relevant research paper (sleep, memory, focus, procrastination, etc.)
2. Translates it into simple, plain English for your audience
3. Generates one concrete task from it
4. Posts it to your Telegram channel

## What you need (2 free accounts)
1. **Telegram bot token** — from @BotFather (you already have this, or are getting it)
2. **Anthropic API key** — free to create at https://console.anthropic.com (used to write the simplified summaries and tasks)

## Setup (one time)

1. Copy `.env.example` to `.env` and fill in your real values:
   - `TELEGRAM_BOT_TOKEN` — from BotFather
   - `TELEGRAM_CHANNEL_ID` — your channel's @username, e.g. `@nuro_channel`
     - **Important:** add your bot as an *admin* of the channel first, or it can't post
   - `ANTHROPIC_API_KEY` — from console.anthropic.com
   - `POST_HOUR` / `POST_MINUTE` — what time to post daily (24h format)
   - `TIMEZONE` — e.g. `Asia/Tashkent`

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Test it locally first:
   ```
   python main.py
   ```
   Then message your bot `/postnow` on Telegram to trigger an immediate test post.

## Making it run 24/7 (free hosting)

Your laptop needs to be on for the bot to run — for it to post automatically every
day without you touching it, deploy it to a free always-on host. Easiest option:

**Railway.app** (free tier, simplest):
1. Create account at railway.app, connect your GitHub
2. Push this folder to a new GitHub repo
3. In Railway: "New Project" → "Deploy from GitHub repo" → select it
4. Add your `.env` values under Railway's "Variables" tab (never upload `.env` itself to GitHub)
5. Done — it now runs continuously in the cloud

I can walk you through any of these steps in more detail when you're ready.

## Files
- `main.py` — the bot itself, scheduler, entry point
- `paper_search.py` — finds new papers (rotates topics, avoids repeats)
- `content_generator.py` — Claude-powered translation + task generation
- `requirements.txt` — dependencies
- `.env.example` — template for your secrets (rename to `.env`, fill in, never share)
