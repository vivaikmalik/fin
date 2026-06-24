"""Neutral backtest engine — the isolation boundary.

Reads the Maker's Signal + prices, produces the Result (OOS equity curve).
Does no judging. This is the only place Maker output is consumed; the
Checker downstream sees only the Result JSON.
"""
from __future__ import annotations
import pandas as pd
from data.ingest import load_prices
from shared.contract import Result, SIGNAL_PATH, ASSET, TRAIN_END


def run() -> Result:
    prices = load_prices()
    sig = pd.read_parquet(SIGNAL_PATH)["position"].reindex(prices.index).fillna(0.0)

    rets = prices["close"].pct_change().fillna(0.0)
    strat = (sig * rets).rename("strat")

    oos = strat[strat.index > TRAIN_END]
    equity = (1.0 + oos).cumprod()

    res = Result(
        asset=ASSET,
        train_end=TRAIN_END,
        dates=[d.strftime("%Y-%m-%d") for d in oos.index],
        oos_returns=oos.tolist(),
        equity_curve=equity.tolist(),
        n_bars=int(len(oos)),
        meta={"turnover": float(sig.diff().abs().sum())},
    )
    res.save()
    return res


if __name__ == "__main__":
    r = run()
    print(f"OOS bars={r.n_bars} final_equity={r.equity_curve[-1]:.3f}")
