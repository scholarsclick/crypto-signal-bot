# 5-Minute Candle Signal Bot (BTC / ETH)

Headless Python bot that fires an UP/DOWN signal at the open of every 5-minute
candle, sends Telegram/Discord alerts, logs every prediction, and tracks its own
live accuracy. Same strategy is also available as a one-file browser app
(`../crypto-signal-bot.html`).

## Files
| File | Purpose |
|------|---------|
| `signal_bot.py` | The live 24/7 bot. |
| `backtest.py`   | Replays the strategy over history, reports accuracy instantly. |
| `indicators.py` | The strategy (EMA/MACD/RSI/Stoch/ROC/volume vote). Shared by both. |
| `data.py`       | Binance public data fetch (no API key). |
| `alerts.py`     | Telegram + Discord delivery. |
| `config.py`     | **Edit this** — symbols, alert tokens, thresholds. |

## Quick start
1. **Backtest first** (no setup needed — see if it's worth running):
   ```
   python backtest.py
   ```
   Use more history: `python backtest.py 2000`

2. **Configure alerts** (optional) in `config.py`:
   - **Telegram:** message `@BotFather` -> `/newbot` -> copy token into
     `TELEGRAM_BOT_TOKEN`. Message your bot once, then open
     `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your `chat id`.
   - **Discord:** Server Settings -> Integrations -> Webhooks -> New Webhook ->
     Copy URL into `DISCORD_WEBHOOK_URL`.
   - Leave either blank to disable it. Blank both = console-only.

3. **Run live:**
   ```
   python signal_bot.py
   ```
   Or just double-click `run_bot.bat`. Stop with `Ctrl+C`.

Predictions and outcomes are appended to `signals_log.csv`.

## Run it in the cloud on GitHub Actions (no PC needed)
This repo ships a workflow at `.github/workflows/signals.yml` that runs
`run_once.py` **every 5 minutes in GitHub's cloud**, fetching live data and
sending your alerts. `run_once.py` is stateless — it recomputes recent accuracy
from live history each run, so nothing needs to persist between runs.

**Setup (2 minutes):**
1. Make sure the repo is **public** — Actions minutes are free & unlimited for
   public repos. (Every-5-min on a private repo would burn the free 2,000
   min/month quota.)
2. Add your alert secrets: repo **Settings -> Secrets and variables -> Actions
   -> New repository secret**. Add any of:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DISCORD_WEBHOOK_URL`.
   Without secrets it still runs and prints signals to the Actions log.
3. **Actions** tab -> enable workflows -> open **5m Candle Signal Bot** ->
   **Run workflow** to test immediately. The schedule then fires every ~5 min.

**Caveats (be honest with yourself):**
- GitHub's scheduled cron is *best-effort* — runs can be delayed several minutes
  under load, so alerts won't land exactly at the candle open.
- GitHub auto-disables scheduled workflows after **60 days** of no repo activity;
  push any commit to re-arm.
- For second-accurate timing, run `signal_bot.py` on an always-on machine/VPS
  instead.

## Honest expectations
Predicting a single 5-minute candle's direction is dominated by noise. A realistic
hit-rate is **50–55%**. `backtest.py` prints an "always-UP" baseline — if the
strategy can't beat that, it isn't adding value. **Educational tool, not financial
advice. Do not trade real money on this alone.**
