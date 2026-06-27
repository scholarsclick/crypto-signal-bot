"""
Configuration for the 5-minute candle signal bot.

Two ways to set secrets:
  * Locally: paste them into the quotes below.
  * On GitHub Actions: set repo Secrets (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    DISCORD_WEBHOOK_URL). Environment variables ALWAYS override the values here.

Leave a channel empty to disable it — the bot simply skips it.
"""
import os

# ----- Markets to trade signals on -----
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVAL = "5m"          # candle size
HISTORY_LIMIT = 200      # how many candles to pull for indicator math

# ----- Telegram alerts (optional) -----
# How to get these:
#   1. In Telegram, message @BotFather -> /newbot -> follow prompts -> copy the token.
#   2. Message your new bot once (say "hi").
#   3. Open: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates  -> find "chat":{"id":...}
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")   # or paste between the quotes
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")     # or paste between the quotes

# ----- Discord alerts (optional) -----
# Server Settings -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")  # or paste between the quotes

# ----- Behaviour -----
ONLY_ALERT_NON_NEUTRAL = True    # don't ping for "NEUTRAL / no edge" candles
MIN_CONFIDENCE_TO_ALERT = 55     # only send alerts at/above this confidence %
LOG_FILE = "signals_log.csv"     # predictions + outcomes are appended here
