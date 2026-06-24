"""Data layer: pull daily OHLCV for the target asset into Parquet.

Parquet chosen for columnar speed + tiny footprint vs CSV/HDF5 for
single-asset daily research. Cache to data/cache to avoid re-download.
"""
from __future__ import annotations
import os
import pandas as pd
from shared.contract import ASSET

CACHE = "data/cache"


def _download(asset: str, start: str) -> pd.DataFrame:
    """yfinance with short backoff — Yahoo intermittently returns HTTP 429."""
    import time
    import yfinance as yf  # lazy: rest of system has no hard dep
    last = None
    for attempt in range(4):
        try:
            df = yf.download(asset, start=start, auto_adjust=True, progress=False)
            if df is not None and not df.empty:
                return df
        except Exception as e:  # noqa: BLE001 — surface only after retries
            last = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"yfinance returned no data for {asset}: {last}")


def load_prices(asset: str = ASSET, start: str = "2005-01-01") -> pd.DataFrame:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{asset.replace('^', '')}.parquet")  # ^VIX -> VIX.parquet
    if os.path.exists(path):
        return pd.read_parquet(path)
    df = _download(asset, start)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)  # ('Close','SPY') -> 'Close'
    df = df[["Close"]].rename(columns={"Close": "close"})
    df.index.name = "date"
    df = df.dropna()
    df.to_parquet(path)
    return df


if __name__ == "__main__":
    # SPY = traded asset; ^VIX = its implied-vol risk signal (Maker risk overlay).
    ok = True
    for asset in (ASSET, "^VIX"):
        df = load_prices(asset)
        n_null = int(df["close"].isna().sum())
        print(f"{asset}: rows={len(df)} "
              f"range={df.index.min().date()}..{df.index.max().date()} nulls={n_null}")
        if len(df) < 1000 or n_null > 0:
            ok = False
    if not ok:
        print("STATUS: DATA INGESTION FAILED")
        raise SystemExit(1)
    print("STATUS: DATA READY")
