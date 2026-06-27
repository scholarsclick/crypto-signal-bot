"""Alert delivery to Telegram and/or Discord. Both are optional."""
import json
import urllib.parse
import urllib.request

import config


def _post(url, data, headers=None):
    req = urllib.request.Request(
        url, data=data, headers=headers or {}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def send_telegram(text):
    token = config.TELEGRAM_BOT_TOKEN.strip()
    chat = config.TELEGRAM_CHAT_ID.strip()
    if not token or not chat:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    ).encode()
    try:
        _post(url, data, {"Content-Type": "application/x-www-form-urlencoded"})
    except Exception as e:  # noqa: BLE001
        print(f"  [telegram] failed: {e}")


def send_discord(text):
    url = config.DISCORD_WEBHOOK_URL.strip()
    if not url:
        return
    data = json.dumps({"content": text}).encode()
    try:
        _post(url, data, {"Content-Type": "application/json"})
    except Exception as e:  # noqa: BLE001
        print(f"  [discord] failed: {e}")


def broadcast(text):
    send_telegram(text)
    send_discord(text)
