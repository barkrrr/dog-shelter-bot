"""
main.py — Queue-based scheduler. Each shelter account is processed one at a time.
If Instagram rate-limits a shelter, it is requeued with an exponential backoff delay
so other shelters continue processing uninterrupted.
"""

import time
import logging
import queue
from dataclasses import dataclass, field
from config import (
    SHELTER_ACCOUNTS, CHECK_INTERVAL_MINUTES,
    FILTER_SIZE, FILTER_MAX_AGE_YEARS, FILTER_MIN_CUTENESS, FILTER_AGE_LABELS
)
from scraper import get_latest_posts, RateLimitError
from agent import analyze_post, DogRecord
from storage import is_new, mark_seen
from notifier import send_alert, send_startup_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# How long to wait before retrying a rate-limited shelter (seconds).
# Doubles on each consecutive failure, up to the maximum.
BACKOFF_INITIAL_SECONDS = 5 * 60    # 5 minutes
BACKOFF_MAX_SECONDS     = 60 * 60   # 1 hour
MAX_RETRIES             = 4


@dataclass(order=True)
class QueueItem:
    process_at: float          # epoch time — item won't be processed before this
    shelter: str = field(compare=False)
    retries: int = field(compare=False, default=0)


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


def process_shelter(shelter: str) -> tuple[int, int]:
    """
    Fetch and analyse new posts for one shelter.
    Returns (new_post_count, match_count).
    Raises RateLimitError if Instagram throttles us.
    """
    posts = get_latest_posts(shelter, max_posts=5)
    new_count = 0
    match_count = 0
    for post in posts:
        if not is_new(shelter, post.shortcode):
            continue
        new_count += 1
        logger.info("New post from @%s — analysing...", shelter)
        dog = analyze_post(post)
        mark_seen(shelter, post.shortcode)
        if matches_filters(dog):
            match_count += 1
            logger.info(
                "✅ Match! %s (%s, %s) — cuteness %s/10",
                dog.name or "unnamed", dog.size, dog.age_label, dog.cuteness_score
            )
            send_alert(dog)
        else:
            reason = "not a dog post" if not dog.is_dog_post else "didn't match filters"
            logger.info("⏭️  Skipped (%s): %s", reason, post.post_url)
    return new_count, match_count


def run_check_cycle(q: queue.PriorityQueue):
    """
    Load all shelters into the queue and drain it one by one.
    Rate-limited shelters are requeued with exponential backoff.
    """
    logger.info("── Starting check cycle across %d shelters ──", len(SHELTER_ACCOUNTS))

    for i, shelter in enumerate(SHELTER_ACCOUNTS):
        q.put(QueueItem(process_at=time.time() + (i * 10 * 60), shelter=shelter))

    total_new = 0
    total_matches = 0

    while not q.empty():
        item = q.get()

        # If the item isn't due yet, wait
        wait = item.process_at - time.time()
        if wait > 0:
            logger.info(
                "⏳ @%s is rate-limited — waiting %.0f seconds before retry %d/%d...",
                item.shelter, wait, item.retries, MAX_RETRIES
            )
            time.sleep(wait)

        try:
            new_count, match_count = process_shelter(item.shelter)
            total_new += new_count
            total_matches += match_count

        except RateLimitError:
            if item.retries >= MAX_RETRIES:
                logger.error(
                    "❌ @%s hit rate limit %d times — skipping for this cycle.",
                    item.shelter, MAX_RETRIES
                )
            else:
                backoff = min(
                    BACKOFF_INITIAL_SECONDS * (2 ** item.retries),
                    BACKOFF_MAX_SECONDS
                )
                logger.warning(
                    "⚠️  Rate limited on @%s — requeuing with %.0f min backoff.",
                    item.shelter, backoff / 60
                )
                q.put(QueueItem(
                    process_at=time.time() + backoff,
                    shelter=item.shelter,
                    retries=item.retries + 1,
                ))

        except Exception as e:
            logger.error("Unexpected error processing @%s: %s", item.shelter, e, exc_info=True)

    logger.info(
        "── Cycle complete. New posts: %d | Matches sent: %d ──",
        total_new, total_matches
    )


def main():
    logger.info("🐾 Dog Shelter Bot starting up")
    logger.info("   Shelters : %s", ", ".join(f"@{s}" for s in SHELTER_ACCOUNTS))
    logger.info("   Interval : every %d minutes", CHECK_INTERVAL_MINUTES)
    logger.info("   Filters  : size=%s | max_age=%s yrs | min_cuteness=%s",
                FILTER_SIZE, FILTER_MAX_AGE_YEARS, FILTER_MIN_CUTENESS)

    send_startup_message()

    q: queue.PriorityQueue = queue.PriorityQueue()

    while True:
        try:
            run_check_cycle(q)
        except Exception as e:
            logger.error("Unexpected error in check cycle: %s", e, exc_info=True)

        logger.info("Sleeping %d minutes until next cycle...", CHECK_INTERVAL_MINUTES)
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
