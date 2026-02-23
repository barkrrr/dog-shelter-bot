"""
notifier.py — Sends a Telegram alert with the dog's photo and key details.
"""

import os
import logging
import requests
from agent import DogRecord

logger = logging.getLogger(__name__)


def _bot_url(method: str) -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"https://api.telegram.org/bot{token}/{method}"


def send_alert(dog: DogRecord):
    """Send a Telegram photo message for a matched dog."""
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    # Build a nicely formatted caption
    lines = ["🐶 *New small dog available for adoption!*\n"]

    if dog.name:
        lines.append(f"*Name:* {dog.name}")
    if dog.breed:
        lines.append(f"*Breed:* {dog.breed}")
    if dog.size:
        lines.append(f"*Size:* {dog.size.capitalize()}")
    if dog.age_label:
        age_str = dog.age_label.capitalize()
        if dog.age_years:
            age_str += f" (~{dog.age_years:.1f} yrs)"
        lines.append(f"*Age:* {age_str}")
    if dog.sex and dog.sex != "unknown":
        lines.append(f"*Sex:* {dog.sex.capitalize()}")
    if dog.cuteness_score:
        lines.append(f"*Cuteness:* {'⭐' * dog.cuteness_score} {dog.cuteness_score}/10")
        if dog.cuteness_reason:
            lines.append(f"_{dog.cuteness_reason}_")
    if dog.summary:
        lines.append(f"\n📝 {dog.summary}")

    lines.append(f"\n🔗 [View post]({dog.post_url})")
    lines.append(f"📍 Shelter: @{dog.shelter}")

    caption = "\n".join(lines)

    # Try to send with photo first, fall back to text-only
    sent = False
    if dog.image_url:
        try:
            resp = requests.post(_bot_url("sendPhoto"), data={
                "chat_id": chat_id,
                "photo": dog.image_url,
                "caption": caption,
                "parse_mode": "Markdown",
            }, timeout=15)
            if resp.ok:
                sent = True
                logger.info("Telegram photo alert sent for %s", dog.name or dog.shortcode)
            else:
                logger.warning("sendPhoto failed: %s", resp.text)
        except Exception as e:
            logger.warning("sendPhoto error: %s", e)

    if not sent:
        try:
            requests.post(_bot_url("sendMessage"), data={
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            }, timeout=15)
            logger.info("Telegram text alert sent for %s", dog.name or dog.shortcode)
        except Exception as e:
            logger.error("sendMessage error: %s", e)


def send_startup_message():
    """Confirm the bot is running — sent once on deploy."""
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    try:
        requests.post(_bot_url("sendMessage"), data={
            "chat_id": chat_id,
            "text": "🐾 Dog Shelter Bot is running! I'll notify you when a matching dog appears.",
        }, timeout=10)
    except Exception as e:
        logger.warning("Could not send startup message: %s", e)
