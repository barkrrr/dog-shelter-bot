# ============================================================
#  🐶 Dog Shelter Bot — Configuration
#  Edit this file in GitHub to change shelters or filters.
# ============================================================

# Instagram usernames of shelters to monitor (without @)
SHELTER_ACCOUNTS = [
    "asociacionalmasbellas",   # ← replace with real usernames
    "ladridosfelices",
    "volver_a_latir",
    "protectora.bcn",
    "apagranollers_protectora",
    "ladridos_vagabundos",
    "protectoralahuellablanca",
    "arcadenoesevilla",
    "protectora_pelescapat"
]

# How often to check for new posts (in minutes)
CHECK_INTERVAL_MINUTES = 120

# ── Filters ──────────────────────────────────────────────────
# Only send a Telegram alert if ALL of these match.
# Set a value to None to disable that filter.

FILTER_SIZE = "small"          # "small" | "medium" | "large" | None
FILTER_MAX_AGE_YEARS = 5       # e.g. 5 means dogs up to 5 years old | None
FILTER_MIN_CUTENESS = 6        # 1–10 | None
FILTER_AGE_LABELS = None       # e.g. ["puppy", "young"] | None to allow all
