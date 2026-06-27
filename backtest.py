"""
Backtest the exact live strategy over recent history.

It walks candle-by-candle: at each step it feeds only the candles available
*up to that point* into build_signal() (no look-ahead), then checks whether the
next candle actually closed in the predicted direction.

Run:
    python backtest.py                 # default ~3 days per symbol
    python backtest.py 2000            # use 2000 candles (~7 days) per symbol
"""
import sys

import config
from data import fetch_klines
from indicators import build_signal

# Indicators need a warm-up window before they are meaningful.
WARMUP = 40


def paginate(symbol, total):
    """Fetch `total` candles by walking backwards (Binance caps 1000/call)."""
    out = []
    end_time = None
    while len(out) < total:
        batch = fetch_klines(symbol, config.INTERVAL,
                             min(1000, total - len(out)), end_time)
        if not batch:
            break
        out = batch + out
        end_time = batch[0]["openTime"] - 1
        if len(batch) < 1000:
            break
    return out


def backtest_symbol(symbol, total):
    candles = paginate(symbol, total)
    n = len(candles)
    if n < WARMUP + 5:
        print(f"{symbol}: not enough data ({n})")
        return

    total_p = correct = up_p = down_p = neutral = 0
    conf_correct = conf_total = 0   # accuracy on >=55% confidence calls
    hi_total = hi_correct = 0

    # Predict candle i using candles[:i]; verify against candles[i].
    for i in range(WARMUP, n):
        sig = build_signal(candles[:i])
        actual_up = candles[i]["c"] >= candles[i]["o"]
        if sig["dir"] == "NEUTRAL":
            neutral += 1
            continue
        total_p += 1
        ok = (sig["dir"] == "UP") == actual_up
        correct += ok
        up_p += sig["dir"] == "UP"
        down_p += sig["dir"] == "DOWN"
        if sig["conf"] >= config.MIN_CONFIDENCE_TO_ALERT:
            conf_total += 1
            conf_correct += ok
        if sig["conf"] >= 65:
            hi_total += 1
            hi_correct += ok

    span_h = n * 5 / 60
    print(f"\n=== {symbol} ===")
    print(f"Candles tested : {n}  (~{span_h:.0f} h / {span_h/24:.1f} days)")
    print(f"Directional predictions: {total_p}  (neutral skipped: {neutral})")
    print(f"  UP calls: {up_p}   DOWN calls: {down_p}")
    if total_p:
        print(f"Overall accuracy        : {correct}/{total_p} "
              f"= {100*correct/total_p:.1f}%")
    if conf_total:
        print(f"Accuracy @>= {config.MIN_CONFIDENCE_TO_ALERT}% conf  : {conf_correct}/{conf_total} "
              f"= {100*conf_correct/conf_total:.1f}%")
    if hi_total:
        print(f"Accuracy @>= 65% conf    : {hi_correct}/{hi_total} "
              f"= {100*hi_correct/hi_total:.1f}%")
    # Baseline: how often candles closed up at all (the naive "always UP" rate)
    ups = sum(1 for c in candles[WARMUP:] if c["c"] >= c["o"])
    base = 100 * ups / (n - WARMUP)
    print(f"Baseline (always-UP)    : {base:.1f}%   <- beat this to add value")


def main():
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 850  # ~3 days of 5m
    print(f"Backtesting {config.SYMBOLS} on {config.INTERVAL} "
          f"over ~{total} candles each...\n(no look-ahead; warm-up {WARMUP} candles)")
    for sym in config.SYMBOLS:
        try:
            backtest_symbol(sym, total)
        except Exception as e:  # noqa: BLE001
            print(f"{sym}: error {e}")
    print("\nReminder: 5m direction is mostly noise. ~50-55% is the honest range.")


if __name__ == "__main__":
    main()
