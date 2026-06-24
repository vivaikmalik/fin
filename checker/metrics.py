"""Risk metrics. Pure functions over a return series — no I/O, no Maker."""
from __future__ import annotations
import numpy as np

TRADING_DAYS = 252


def sharpe(returns: list[float], rf: float = 0.0) -> float:
    r = np.asarray(returns, dtype=float)
    if r.std(ddof=1) == 0 or len(r) < 2:
        return 0.0
    excess = r - rf / TRADING_DAYS
    return float(np.sqrt(TRADING_DAYS) * excess.mean() / excess.std(ddof=1))


def max_drawdown(equity_curve: list[float]) -> float:
    e = np.asarray(equity_curve, dtype=float)
    if len(e) == 0:
        return 0.0
    peak = np.maximum.accumulate(e)
    return float((1.0 - e / peak).max())
