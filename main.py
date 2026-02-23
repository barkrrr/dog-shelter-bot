"""
main.py — The scheduler loop. Checks all shelters every N minutes,
runs new posts through the Claude agent, and fires Telegram alerts for matches.
"""

import time
import logging
import os
from config import SHELTER_ACCOUNTS, CHECK_INTERVAL_MINUTES, FILTER_SIZE, FILTER_MAX_AGE_YEARS, FILTER_MIN_CUTENESS, FILTER_AGE_LABELS
from scraper import get_latest_posts
from agent import analyze_post, DogRecord
from storage import is_new, mark_seen
from notifier import send_alert, send_startup_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def matches_filters(dog: DogRecord) -> bool:
    """Return True if this dog passes all configured filters."""
    if not dog.is_dog_post:
        return False

    if FILTER_SIZE and dog.size != FILTER_SIZE:
        return False

    if FILTER_MAX_AGE_YEARS is not None and dog.age_years is not None:
        if dog.age_years > FILTER_MAX_AGE_YEARS:
            return False

    if FILTER_MIN_CUTENESS is not None and dog.cuteness_score is not None:
        if dog.cuteness_score < FILTER_MIN_CUTENESS:
            return False

    if FILTER_AGE_LABELS and dog.age_label not in FILTER_AGE_LABELS:
        return False

    return True


def run_check():
    """Single check cycle across all shelter accounts."""
    logger.info("── Starting check across %d shelters ──", len(SHELTER_ACCOUNTS))
    new_count = 0
    match_count = 0

    for shelter in SHELTER_ACCOUNTS:
        posts = get_latest_posts(shelter, max_posts=5)
        for post in posts:
            if not is_new(shelter, post.shortcode):
                continue

            new_count += 1
            logger.info("New post from @%s — analysing...", shelter)
            dog = analyze_post(post)
            mark_seen(shelter, post.shortcode)

            if matches_filters(dog):
                match_count += 1
                logger.info("✅ Match! %s (%s, %s) — cuteness %s/10",
                            dog.name or "unnamed", dog.size, dog.age_label, dog.cuteness_score)
                send_alert(dog)
            else:
                reason = "not a dog post" if not dog.is_dog_post else "didn't match filters"
                logger.info("⏭️  Skipped (%s): %s", reason, post.post_url)

        time.sleep(2)  # small pause between shelters

    logger.info("── Check complete. New posts: %d | Matches sent: %d ──", new_count, match_count)


def main():
    logger.info("🐾 Dog Shelter Bot starting up")
    logger.info("   Shelters: %s", ", ".join(f"@{s}" for s in SHELTER_ACCOUNTS))
    logger.info("   Check interval: every %d minutes", CHECK_INTERVAL_MINUTES)
    logger.info("   Filters: size=%s | max_age=%s | min_cuteness=%s",
                FILTER_SIZE, FILTER_MAX_AGE_YEARS, FILTER_MIN_CUTENESS)

    send_startup_message()

    while True:
        try:
            run_check()
        except Exception as e:
            logger.error("Unexpected error during check: %s", e, exc_info=True)

        logger.info("Sleeping %d minutes until next check...", CHECK_INTERVAL_MINUTES)
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
