"""
scraper.py — Fetches the latest posts from Instagram shelter accounts.
Uses instaloader for reliability. Credentials are optional but recommended.
"""

import os
import time
import random
import base64
import logging
import requests
import instaloader
from io import BytesIO
from PIL import Image
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Initialise a single loader instance (reused across checks)
_loader: Optional[instaloader.Instaloader] = None


def get_loader() -> instaloader.Instaloader:
    global _loader
    if _loader is None:
        _loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            save_metadata=False,
            quiet=True,
        )
        ig_user = os.getenv("INSTAGRAM_USERNAME")
        ig_pass = os.getenv("INSTAGRAM_PASSWORD")
        if ig_user and ig_pass:
            try:
                _loader.login(ig_user, ig_pass)
                logger.info("Logged in to Instagram as %s", ig_user)
            except Exception as e:
                logger.warning("Instagram login failed: %s — continuing without login", e)
    return _loader


@dataclass
class RawPost:
    shelter: str
    shortcode: str
    post_url: str
    caption: str
    image_url: str
    image_b64: Optional[str]
    timestamp: str


def fetch_image_b64(url: str, max_size_px: int = 800) -> Optional[str]:
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        img.thumbnail((max_size_px, max_size_px))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        logger.warning("Could not fetch image: %s", e)
        return None


def get_latest_posts(shelter: str, max_posts: int = 5) -> list[RawPost]:
    """Return the N most recent posts from a shelter account."""
    loader = get_loader()
    posts = []
    try:
        profile = instaloader.Profile.from_username(loader.context, shelter)
        for i, post in enumerate(profile.get_posts()):
            if i >= max_posts:
                break
            image_b64 = fetch_image_b64(post.url)
            posts.append(RawPost(
                shelter=shelter,
                shortcode=post.shortcode,
                post_url=f"https://www.instagram.com/p/{post.shortcode}/",
                caption=post.caption or "",
                image_url=post.url,
                image_b64=image_b64,
                timestamp=str(post.date_utc),
            ))
            time.sleep(random.uniform(1.5, 3.0))
    except instaloader.exceptions.ProfileNotExistsException:
        logger.error("Profile @%s not found — check username in config.py", shelter)
    except Exception as e:
        logger.error("Error fetching @%s: %s", shelter, e)
    return posts
