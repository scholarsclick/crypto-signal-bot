"""Binance public market-data fetching (no API key required)."""
import json
import urllib.request

BASES = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api4.binance.com",
]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "signal-bot/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fetch_klines(symbol, interval="5m", limit=200, end_time=None):
    """Return a list of candle dicts, oldest first. Tries mirrors on failure."""
    q = f"symbol={symbol}&interval={interval}&limit={limit}"
    if end_time is not None:
        q += f"&endTime={end_time}"
    last_err = None
    for base in BASES:
        try:
            raw = _get(f"{base}/api/v3/klines?{q}")
            return [
                {
                    "openTime": c[0], "o": float(c[1]), "h": float(c[2]),
                    "l": float(c[3]), "c": float(c[4]), "v": float(c[5]),
                    "closeTime": c[6],
                }
                for c in raw
            ]
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"All Binance mirrors failed: {last_err}")
