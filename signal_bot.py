"""
Live 5-minute candle signal bot — headless, runs 24/7.

At the open of every 5-minute candle it:
  1. Evaluates the prediction made for the candle that just closed (correct?).
  2. Builds a fresh UP/DOWN signal for the new candle.
  3. Sends Telegram/Discord alerts (if configured) and logs to CSV.

Run:  python signal_bot.py
Stop: Ctrl+C
"""
import csv
import os
import sys
import time
from datetime import datetime, timezone

# Windows consoles default to cp1252, which can't print ▲ ✓ etc. Force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

import config
from data import fetch_klines
from indicators import build_signal
from alerts import broadcast

_TF_MIN = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
INTERVAL_MS = _TF_MIN.get(config.INTERVAL, 5) * 60 * 1000

# In-memory record of the last prediction per symbol, so we can score it
# once its candle closes. Persisted nowhere but the CSV log.
pending = {}            # symbol -> {"openTime", "signal", "conf", "open"}
stats = {s: {"correct": 0, "total": 0} for s in config.SYMBOLS}


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_log():
    if not os.path.exists(config.LOG_FILE):
        with open(config.LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow(
                ["logged_utc", "symbol", "candle_open_utc", "signal",
                 "confidence", "open_price", "close_price", "result"]
            )


def log_row(row):
    with open(config.LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow(row)


def ms_to_iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%H:%M:%S")


def cycle(announce=True):
    for sym in config.SYMBOLS:
        try:
            k = fetch_klines(sym, config.INTERVAL, config.HISTORY_LIMIT)
        except Exception as e:  # noqa: BLE001
            print(f"[{now_utc()}] {sym} fetch failed: {e}")
            continue

        forming = k[-1]            # in-progress candle
        closed = k[:-1]            # fully closed candles
        just_closed = closed[-1]

        # 1) Score previous prediction
        p = pending.get(sym)
        if p and p["openTime"] == just_closed["openTime"] and p["signal"] != "NEUTRAL":
            actual_up = just_closed["c"] >= just_closed["o"]
            correct = (p["signal"] == "UP") == actual_up
            stats[sym]["total"] += 1
            if correct:
                stats[sym]["correct"] += 1
            acc = stats[sym]
            print(f"[{now_utc()}] {sym} candle {ms_to_iso(just_closed['openTime'])} "
                  f"closed {'UP' if actual_up else 'DOWN'} — predicted {p['signal']} "
                  f"=> {'✓ CORRECT' if correct else '✗ wrong'} "
                  f"| live acc {acc['correct']}/{acc['total']} "
                  f"({100*acc['correct']//max(1,acc['total'])}%)")
            log_row([now_utc(), sym, ms_to_iso(just_closed["openTime"]),
                     p["signal"], p["conf"], p["open"], just_closed["c"],
                     "correct" if correct else "wrong"])

        # 2) New signal for the forming candle
        sig = build_signal(closed)
        top = sorted(sig["votes"], key=lambda v: abs(v[1] * v[2]), reverse=True)[:3]
        reasons = ", ".join(f"{n}{'▲' if v > 0 else '▼' if v < 0 else '·'}"
                            for n, v, _ in top)
        print(f"[{now_utc()}] {sym} NEW 5m candle {ms_to_iso(forming['openTime'])} "
              f"-> {sig['dir']} {sig['conf']}%  @ ${sig['price']:,.2f} "
              f"| {reasons}")

        pending[sym] = {"openTime": forming["openTime"], "signal": sig["dir"],
                        "conf": sig["conf"], "open": forming["o"]}

        # 3) Alerts
        if announce and sig["dir"] != "NEUTRAL" and sig["conf"] >= config.MIN_CONFIDENCE_TO_ALERT:
            arrow = "🟢⬆️" if sig["dir"] == "UP" else "🔴⬇️"
            acc = stats[sym]
            msg = (f"{arrow} <b>{sym}</b> 5m signal: <b>{sig['dir']}</b> "
                   f"({sig['conf']}%)\n"
                   f"Price ${sig['price']:,.2f} · RSI {sig['rsi']:.0f}\n"
                   f"Candle opens {ms_to_iso(forming['openTime'])} UTC\n"
                   f"Top factors: {reasons}\n"
                   f"Live accuracy: {acc['correct']}/{acc['total']}")
            broadcast(msg)


def ms_to_next_candle():
    return INTERVAL_MS - (int(time.time() * 1000) % INTERVAL_MS)


def main():
    ensure_log()
    print("=" * 64)
    print(" 5-MIN CANDLE SIGNAL BOT — live")
    print(f" Symbols: {', '.join(config.SYMBOLS)}  | interval: {config.INTERVAL}")
    tg = "ON" if config.TELEGRAM_BOT_TOKEN else "off"
    dc = "ON" if config.DISCORD_WEBHOOK_URL else "off"
    print(f" Alerts: Telegram {tg} · Discord {dc} · min conf {config.MIN_CONFIDENCE_TO_ALERT}%")
    print(f" Logging to: {config.LOG_FILE}")
    print(" Press Ctrl+C to stop.")
    print("=" * 64)

    # Prime predictions immediately (no alert on the first pass).
    cycle(announce=False)

    while True:
        wait = ms_to_next_candle() / 1000 + 2  # +2s buffer for candle to exist
        time.sleep(wait)
        cycle(announce=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
