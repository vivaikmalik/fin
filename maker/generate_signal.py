"""Maker entrypoint: run the active strategy, write the Signal contract file.

Placeholder strategy = dual moving-average trend filter. The autonomous
loop (run_quant_loop) mutates THIS logic when the Checker rejects a result.
"""
from __future__ import annotations
import pandas as pd
from data.ingest import load_prices
from maker.strategy_template import Strategy
from shared.contract import SIGNAL_PATH


class TrendMA(Strategy):
    name = "trend_ma_50_200"

    def __init__(self, fast: int = 50, slow: int = 200):
        self.fast, self.slow = fast, slow

    def signal(self, prices: pd.DataFrame) -> pd.Series:
        c = prices["close"]
        sig = (c.rolling(self.fast).mean() > c.rolling(self.slow).mean()).astype(float)
        return sig.shift(1).fillna(0.0)  # shift: trade next bar, no look-ahead


def main() -> None:
    prices = load_prices()
    sig = TrendMA().signal(prices).rename("position")
    sig.to_frame().to_parquet(SIGNAL_PATH)
    print(f"wrote {len(sig)} signals -> {SIGNAL_PATH}")


if __name__ == "__main__":
    main()
