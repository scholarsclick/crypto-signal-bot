"""
ONE-SHOT signal run — designed for GitHub Actions (or any cron).

Unlike signal_bot.py (which loops forever), this runs a single pass and exits,
so it works perfectly as a scheduled job. It is fully STATELESS: it recomputes
the prediction for the candle that just closed and a rolling recent-accuracy
figure directly from live history, so nothing needs to be stored between runs.

Run:  python run_once.py
"""
import sys
from datetime import datetime, timezone

import config
from data import fetch_klines
from indicators import build_signal
from alerts import broadcast

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROLLING = 100  # candles used for the "recent accuracy" figure


def ms_to_iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%H:%M:%S")


def rolling_accuracy(closed, lookback=ROLLING):
    """Walk-forward over the last `lookback` closed candles. No look-ahead."""
    start = max(2, len(closed) - lookback)
    correct = total = 0
    for i in range(start, len(closed)):
        sig = build_signal(closed[:i])
        if sig["dir"] == "NEUTRAL":
            continue
        actual_up = closed[i]["c"] >= closed[i]["o"]
        total += 1
        if (sig["dir"] == "UP") == actual_up:
            correct += 1
    return correct, total


def main():
    for sym in config.SYMBOLS:
        try:
            k = fetch_klines(sym, config.INTERVAL, 300)
        except Exception as e:  # noqa: BLE001
            print(f"{sym}: fetch failed: {e}")
            continue

        forming = k[-1]          # currently-forming candle
        closed = k[:-1]          # fully closed candles
        just_closed = closed[-1]

        # Did the previous candle's prediction pan out? (recomputed, stateless)
        prev_sig = build_signal(closed[:-1])
        actual_up = just_closed["c"] >= just_closed["o"]
        if prev_sig["dir"] != "NEUTRAL":
            prev_ok = (prev_sig["dir"] == "UP") == actual_up
            verdict = "✓ CORRECT" if prev_ok else "✗ wrong"
        else:
            verdict = "neutral (no call)"

        cor, tot = rolling_accuracy(closed)
        acc_str = f"{cor}/{tot} ({100*cor//max(1,tot)}%)" if tot else "n/a"

        sig = build_signal(closed)
        top = sorted(sig["votes"], key=lambda v: abs(v[1] * v[2]), reverse=True)[:3]
        reasons = ", ".join(f"{n}{'▲' if v > 0 else '▼' if v < 0 else '·'}"
                            for n, v, _ in top)

        print(f"{sym}: last candle {ms_to_iso(just_closed['openTime'])} "
              f"closed {'UP' if actual_up else 'DOWN'} | prev signal {prev_sig['dir']} "
              f"=> {verdict} | rolling acc {acc_str}")
        print(f"  NEW candle {ms_to_iso(forming['openTime'])} UTC -> "
              f"{sig['dir']} {sig['conf']}%  @ ${sig['price']:,.2f} | {reasons}")

        if sig["dir"] != "NEUTRAL" and sig["conf"] >= config.MIN_CONFIDENCE_TO_ALERT:
            arrow = "🟢⬆️" if sig["dir"] == "UP" else "🔴⬇️"
            msg = (f"{arrow} <b>{sym}</b> 5m signal: <b>{sig['dir']}</b> "
                   f"({sig['conf']}%)\n"
                   f"Price ${sig['price']:,.2f} · RSI {sig['rsi']:.0f}\n"
                   f"Candle opens {ms_to_iso(forming['openTime'])} UTC\n"
                   f"Top factors: {reasons}\n"
                   f"Recent accuracy: {acc_str}")
            broadcast(msg)


if __name__ == "__main__":
    main()
