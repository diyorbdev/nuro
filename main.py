"""
Nuro Telegram Bot — main entry point.

Runs a daily job that:
1. Finds a new, relevant research paper
2. Simplifies it into plain English using Claude
3. Generates a concrete daily task from it
4. Posts both to your Telegram channel

Also supports manual trigger via /postnow command (message the bot directly, admin only).
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from paper_search import get_daily_paper
from content_generator import build_daily_post

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
POST_HOUR = int(os.environ.get("POST_HOUR", 7))
POST_MINUTE = int(os.environ.get("POST_MINUTE", 0))
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Tashkent")


async def post_daily_content(app: Application):
    """The core job: find a paper, generate content, post it."""
    logger.info("Running daily content job...")
    paper = get_daily_paper()

    if paper is None:
        logger.warning("No new paper found today; skipping post.")
        return

    try:
        message = build_daily_post(paper)
        await app.bot.send_message(
            chat_id=CHANNEL_ID, text=message, parse_mode="Markdown", disable_web_page_preview=False
        )
        logger.info(f"Posted: {paper['title']}")
    except Exception as e:
        logger.error(f"Failed to post daily content: {e}")


async def postnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual trigger: send /postnow to the bot to post immediately (for testing)."""
    await update.message.reply_text("Fetching a paper and building today's post...")
    await post_daily_content(context.application)
    await update.message.reply_text("Done — check the channel.")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Nuro bot is running. It posts automatically every day.\n"
        "Send /postnow to trigger a post immediately (for testing)."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("postnow", postnow_command))

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        post_daily_content,
        trigger=CronTrigger(hour=POST_HOUR, minute=POST_MINUTE),
        args=[app],
    )
    scheduler.start()

    logger.info(f"Nuro bot starting. Daily posts scheduled for {POST_HOUR:02d}:{POST_MINUTE:02d} {TIMEZONE}.")
    app.run_polling()


if __name__ == "__main__":
    main()
