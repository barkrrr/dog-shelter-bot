# 🐶 Dog Shelter Bot

Monitors Instagram shelter accounts and sends you a Telegram alert whenever a small, cute dog is posted for adoption.

---

## Setup Guide (no local dev environment needed)

### Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts to name your bot
3. BotFather will give you a **bot token** — save it (looks like `123456:ABC-DEF...`)
4. Search for your new bot in Telegram and press **Start**
5. To get your **chat ID**, message **@userinfobot** — it will reply with your ID

---

### Step 2 — Deploy to Railway

1. Go to [railway.app](https://railway.app) and sign up with your GitHub account
2. Click **New Project → Deploy from GitHub repo**
3. Select this repository
4. Railway will detect the project and start building automatically

---

### Step 3 — Set environment variables in Railway

In your Railway project dashboard → **Variables**, add these:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your key from console.anthropic.com |
| `TELEGRAM_BOT_TOKEN` | From BotFather (Step 1) |
| `TELEGRAM_CHAT_ID` | From @userinfobot (Step 1) |
| `INSTAGRAM_USERNAME` | *(optional)* Your Instagram username |
| `INSTAGRAM_PASSWORD` | *(optional)* Your Instagram password |

Instagram credentials are optional but improve reliability and rate limits.

---

### Step 4 — Configure shelters and filters

Edit `config.py` directly in GitHub to:
- Add real shelter Instagram usernames to `SHELTER_ACCOUNTS`
- Adjust `FILTER_SIZE`, `FILTER_MAX_AGE_YEARS`, `FILTER_MIN_CUTENESS`
- Change `CHECK_INTERVAL_MINUTES` (default: 30)

Every time you save a change in GitHub, Railway will auto-redeploy.

---

## How it works

```
Every 30 minutes:
  For each shelter account:
    → Fetch latest 5 posts from Instagram
    → Skip posts already seen (tracked in seen_posts.json)
    → Send new posts to Claude (vision + text analysis)
    → Claude extracts: size, age, breed, name, sex
    → Claude scores cuteness 1–10
    → If post matches your filters → Telegram alert with photo
```

## Files

| File | Purpose |
|---|---|
| `config.py` | Shelter list + filter settings — **edit this** |
| `main.py` | Main scheduler loop |
| `scraper.py` | Instagram fetching via instaloader |
| `agent.py` | Claude analysis (tool use) |
| `notifier.py` | Telegram alerts |
| `storage.py` | Tracks seen posts to avoid duplicates |
