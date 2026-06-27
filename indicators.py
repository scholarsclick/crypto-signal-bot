"""
Pure-Python technical indicators and the signal engine.

This is the single source of truth for the strategy. Both the live bot
(signal_bot.py) and the backtester (backtest.py) import buildSignal() from
here, so live and backtested results use identical logic.
"""
import math


def ema(values, period):
    k = 2 / (period + 1)
    e = values[0]
    out = [e]
    for v in values[1:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def rsi(closes, period=14):
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += d if d > 0 else 0
        losses += -d if d < 0 else 0
    ag, al = gains / period, losses / period
    out = [50.0] * period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + (d if d > 0 else 0)) / period
        al = (al * (period - 1) + (-d if d < 0 else 0)) / period
        out.append(100.0 if al == 0 else 100 - 100 / (1 + ag / al))
    return out


def macd(closes, f=12, s=26, sig=9):
    ef, es = ema(closes, f), ema(closes, s)
    line = [a - b for a, b in zip(ef, es)]
    signal = ema(line, sig)
    hist = [a - b for a, b in zip(line, signal)]
    return line, signal, hist


def stochastic(highs, lows, closes, period=14):
    out = []
    for i in range(len(closes)):
        if i < period - 1:
            out.append(50.0)
            continue
        window = range(i - period + 1, i + 1)
        hh = max(highs[j] for j in window)
        ll = min(lows[j] for j in window)
        out.append(50.0 if hh == ll else 100 * (closes[i] - ll) / (hh - ll))
    return out


def roc(closes, n=5):
    out = [0.0] * len(closes)
    for i in range(n, len(closes)):
        out[i] = 100 * (closes[i] - closes[i - n]) / closes[i - n]
    return out


def sma(arr, n, end):
    return sum(arr[end - n + 1:end + 1]) / n


def clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def build_signal(k):
    """
    k: list of CLOSED candles, each a dict with o, h, l, c, v.
    Returns a signal dict predicting the direction of the NEXT (forming) candle.
    """
    closes = [x["c"] for x in k]
    highs = [x["h"] for x in k]
    lows = [x["l"] for x in k]
    vols = [x["v"] for x in k]
    last = len(closes) - 1

    ema9, ema21 = ema(closes, 9), ema(closes, 21)
    r = rsi(closes, 14)
    _, _, hist = macd(closes)
    st = stochastic(highs, lows, closes, 14)
    rc = roc(closes, 5)

    votes = []

    def add(label, val, weight):
        votes.append((label, clamp(val), weight))

    # 1) EMA trend + slope
    trend = (ema9[last] - ema21[last]) / closes[last] * 1000
    slope = (ema9[last] - ema9[last - 1]) / closes[last] * 2000
    add("EMA9/21 trend", math.tanh(trend), 1.2)
    add("EMA9 slope", math.tanh(slope), 0.8)

    # 2) MACD histogram value + momentum
    hist_now, hist_prev = hist[last], hist[last - 1]
    add("MACD hist", math.tanh(hist_now / closes[last] * 1500), 0.8)
    delta = hist_now - hist_prev
    add("MACD momentum",
        (1 if delta > 0 else -1) * min(1, abs(delta) / closes[last] * 3000), 0.7)

    # 3) RSI
    rsi_now, rsi_prev = r[-1], r[-2]
    if rsi_now < 32:
        rsi_vote = 0.7
    elif rsi_now > 68:
        rsi_vote = -0.7
    else:
        rsi_vote = math.tanh((rsi_now - rsi_prev) / 8) + (rsi_now - 50) / 100
    add(f"RSI({rsi_now:.0f})", rsi_vote, 0.9)

    # 4) Stochastic
    st_now = st[last]
    st_vote = 0.6 if st_now < 20 else -0.6 if st_now > 80 else (st_now - 50) / 60
    add("Stoch", st_vote, 0.6)

    # 5) ROC
    add("ROC", math.tanh(rc[last] / 0.8), 0.8)

    # 6) Volume-weighted last candle body
    body = (closes[last] - k[last]["o"]) / closes[last]
    vol_ratio = vols[last] / sma(vols, 20, last)
    add("Vol/Body", math.tanh(body * 4000) * min(1.3, vol_ratio) / 1.3, 0.7)

    # 7) Micro-structure of last 3 closes
    micro = (1 if (closes[last] - closes[last - 1]) +
             (closes[last - 1] - closes[last - 2]) * 0.6 > 0 else -1)
    add("Micro-structure", micro * 0.8, 0.5)

    sw = sum(v * w for _, v, w in votes)
    tw = sum(w for _, _, w in votes)
    score = sw / tw
    direction = "UP" if score > 0.03 else "DOWN" if score < -0.03 else "NEUTRAL"
    conf = min(92, round(50 + min(0.92, abs(score)) * 46))

    return {
        "dir": direction,
        "conf": conf,
        "score": score,
        "price": closes[last],
        "rsi": rsi_now,
        "votes": votes,
    }
