#!/usr/bin/env python3
"""Daily forward-test executor for the FROZEN KalmanTrendMR strategy.

Run once per trading day shortly before the close. Workflow:
  1. Ingest the freshest daily SPY + ^VIX bars (forces a re-download so today's
     latest print is captured).
  2. Compute today's raw target position (post-0.15 deadband) from the frozen
     strategy — i.e. the position to hold into the next session.
  3. Compare to the previously persisted target to decide REBALANCE vs HOLD.
  4. If DISCORD_WEBHOOK_URL is set, post a clean Discord embed.
  5. Execution guard: any failure / NaN data -> critical Discord alert + log +
     non-zero exit.

Nothing here mutates the strategy: it only *reads* the frozen KalmanTrendMR.
Run from the project root:  python prod_signal.py
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import sys
import traceback
import urllib.request

import numpy as np

from data.ingest import load_prices
from maker.generate_signal import KalmanTrendMR
from shared.contract import ASSET, VOL

STATE_FILE = "data/prod_state.json"          # last acted-on target (audit / compare)
LOG_FILE = "logs/prod_signal.log"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8")
log = logging.getLogger("prod_signal")

# Emojis live in the Discord payload (UTF-8 JSON). Windows consoles default to
# cp1252; make local stdout/stderr UTF-8 too so informational output can never
# crash a run. Local print lines are kept ASCII regardless (cron-log friendly).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort
        pass


# --------------------------------------------------------------------------- #
# Discord
# --------------------------------------------------------------------------- #
def _post_discord(payload: dict) -> None:
    """Best-effort webhook POST. Never raises (so it can't break execution)."""
    if not WEBHOOK:
        log.info("DISCORD_WEBHOOK_URL not set - skipping notification")
        return
    try:
        req = urllib.request.Request(
            WEBHOOK, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:  # noqa: BLE001 — notification must not crash the run
        log.error("Discord POST failed: %s", e)


def _critical_alert(msg: str) -> None:
    """Loud failure broadcast (data outage, NaN, any unhandled error)."""
    log.critical(msg)
    _post_discord({"embeds": [{
        "title": "🔴 CRITICAL — prod_signal failed",
        "description": f"```{msg[:1800]}```",
        "color": 0xE01E1E,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "footer": {"text": f"{ASSET} forward-test · manual check required"},
    }]})


def _classify(prev: float | None, today: float) -> tuple[str, int, bool]:
    """Map (previous, today) target -> (alert text, embed color, is_rebalance)."""
    if prev is None or abs(today - prev) < 1e-9:
        return f"✅ HOLD POSITION: NO CHANGE [{today:.2f}]", 0x2ECC71, False
    if today <= 1e-9:
        return "🚨 REBALANCE: MOVE TO FLAT [0.0]", 0xE67E22, True
    if today >= 1.0 - 1e-9:
        return "🚀 REBALANCE: MOVE TO LONG [1.0]", 0x3498DB, True
    return f"🔁 REBALANCE: ADJUST TO [{today:.2f}] (was {prev:.2f})", 0x9B59B6, True


# --------------------------------------------------------------------------- #
# State tracking
# --------------------------------------------------------------------------- #
def _read_state() -> tuple[float | None, str | None]:
    try:
        with open(STATE_FILE) as f:
            s = json.load(f)
        return float(s["target"]), s.get("date")
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return None, None


def _write_state(target: float, date: str) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"target": target, "date": date,
                   "updated": dt.datetime.now(dt.timezone.utc).isoformat()}, f, indent=2)


# --------------------------------------------------------------------------- #
# Main workflow
# --------------------------------------------------------------------------- #
def run() -> int:
    # 1. Freshest data — force a re-download so today's latest bar is included.
    prices = load_prices(ASSET, refresh=True)
    load_prices(VOL, refresh=True)   # refresh the vol cache the strategy reads internally

    if prices.empty or prices["close"].tail(1).isna().any():
        raise ValueError(f"{ASSET}: empty frame or NaN latest close from ingestion")
    close = float(prices["close"].iloc[-1])
    asof = prices.index[-1].date().isoformat()
    if not np.isfinite(close):
        raise ValueError(f"{ASSET}: non-finite close {close!r}")

    # 2. Frozen strategy — raw (unshifted) target = position to hold next session.
    comp = KalmanTrendMR().components(prices)
    row = comp.iloc[-1]
    if not np.isfinite(row["target"]):
        raise ValueError("strategy produced a NaN target")
    today = round(float(row["target"]), 4)

    # 3. State comparison vs the previous target (fall back to the series' own
    #    prior bar on a cold start so a same-day move is still detected).
    prev, prev_date = _read_state()
    if prev is None and len(comp) >= 2:
        prev = round(float(comp["target"].iloc[-2]), 4)
        prev_date = comp.index[-2].date().isoformat()
    label, color, rebalance = _classify(prev, today)

    # 4. Discord embed.
    _post_discord({"embeds": [{
        "title": f"📈 KalmanTrendMR — {ASSET} daily signal",
        "color": color,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fields": [
            {"name": "Date / Close", "value": f"`{asof}`  ·  **${close:,.2f}**", "inline": True},
            {"name": "Trend ensemble", "value": f"`{row['trend']:.2f}` / 1.00", "inline": True},
            {"name": f"{VOL} slope (norm)",
             "value": f"`{row['vix_slope']:+.4f}`  ({row['vix_slope_norm']:.2f})", "inline": True},
            {"name": "Action", "value": label, "inline": False},
            {"name": "Prev target", "value": f"`{prev if prev is not None else 'n/a'}`"
             f"  ({prev_date or 'n/a'})", "inline": True},
            {"name": "Risk scaler", "value": f"`{row['risk']:.2f}`", "inline": True},
        ],
        "footer": {"text": "frozen params · 0.15 deadband · signal for next session"},
    }]})

    # 5. Persist and report.
    _write_state(today, asof)
    log.info("asof=%s close=%.2f target=%.2f prev=%s trend=%.2f vix_slope=%+.4f %s",
             asof, close, today, prev, row["trend"], row["vix_slope"],
             "REBALANCE" if rebalance else "HOLD")
    print(f"[{asof}] {ASSET} close=${close:,.2f} target={today} "
          f"trend={row['trend']:.2f} {VOL}_slope={row['vix_slope']:+.4f} "
          f"action={'REBALANCE' if rebalance else 'HOLD'}")
    return 0


def main() -> int:
    try:
        return run()
    except Exception as e:  # noqa: BLE001 — guard: alert on ANY failure
        tb = traceback.format_exc()
        log.error("prod_signal aborted: %s\n%s", e, tb)
        _critical_alert(f"{type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
