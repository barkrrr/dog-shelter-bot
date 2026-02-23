"""
storage.py — Tracks which post IDs have already been seen.
Uses a local JSON file so state survives app restarts on Railway.
"""

import json
import os
from pathlib import Path

STORAGE_FILE = Path("seen_posts.json")


def _load() -> dict:
    if STORAGE_FILE.exists():
        try:
            return json.loads(STORAGE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save(data: dict):
    STORAGE_FILE.write_text(json.dumps(data, indent=2))


def is_new(shelter: str, post_shortcode: str) -> bool:
    """Return True if this post has not been seen before."""
    data = _load()
    seen = data.get(shelter, [])
    return post_shortcode not in seen


def mark_seen(shelter: str, post_shortcode: str):
    """Record that we've processed this post."""
    data = _load()
    seen = data.get(shelter, [])
    if post_shortcode not in seen:
        seen.append(post_shortcode)
        # Keep only last 200 per shelter to avoid unbounded growth
        data[shelter] = seen[-200:]
        _save(data)
