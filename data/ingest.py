"""Data layer: pull daily OHLCV for the target asset into Parquet.

Parquet chosen for columnar speed + tiny footprint vs CSV/HDF5 for
single-asset daily research. Cache to data/cache to avoid re-download.
"""
from __future__ import annotations
import os
import pandas as pd
from shared.contract import ASSET

CACHE = "data/cache"


def load_prices(asset: str = ASSET, start: str = "2005-01-01") -> pd.DataFrame:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{asset}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    import yfinance as yf  # imported lazily so the rest of the system has no hard dep
    df = yf.download(asset, start=start, auto_adjust=True, progress=False)
    df = df[["Close"]].rename(columns={"Close": "close"})
    df.index.name = "date"
    df.to_parquet(path)
    return df


if __name__ == "__main__":
    print(load_prices().tail())
