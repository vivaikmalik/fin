"""Maker entrypoint: run the active strategy, write the Signal contract file.

Active strategy = Kalman trend/mean-reversion blend + VIX risk overlay
(mutated from the placeholder dual-MA by run_quant_loop; see
architecture_decisions.log):
  1. A multi-speed Kalman local-linear-trend ENSEMBLE gives long/flat
     direction (robust trend following, no fixed lookback).
  2. A Kalman-level MEAN-REVERSION sleeve buys short-term dips, but only
     while the trend ensemble confirms an uptrend (avoids falling knives).
  3. Blend = 0.6*trend + 0.4*mr, a weakly-correlated mix that lifts
     risk-adjusted return and cuts drawdown vs trend alone.
  4. A Kalman VIX-slope RISK OVERLAY scales the blend down when implied
     volatility is *rising* (risk-off front-runs drawdowns). Position is
     always 100% on SPY; ^VIX is only an input signal.
The autonomous loop mutates THIS logic when the Checker rejects a result.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from data.ingest import load_prices
from maker.strategy_template import Strategy
from shared.contract import SIGNAL_PATH, ASSET, VOL


def _llt_trend(logp: np.ndarray, q_level: float, q_trend: float, r: float = 1e-4) -> np.ndarray:
    """Causal Kalman local-linear-trend: return the latent slope (velocity) per bar."""
    x = np.array([logp[0], 0.0]); P = np.eye(2)
    F = np.array([[1.0, 1.0], [0.0, 1.0]]); H = np.array([1.0, 0.0])
    Q = np.diag([q_level, q_trend])
    trend = np.empty(len(logp))
    for t in range(len(logp)):
        x = F @ x; P = F @ P @ F.T + Q
        S = H @ P @ H + r; K = (P @ H) / S
        x = x + K * (logp[t] - H @ x); P = P - np.outer(K, H @ P)
        trend[t] = x[1]
    return trend


def _kalman_level(logp: np.ndarray, q: float, r: float = 1.0) -> np.ndarray:
    """Causal Kalman local-level: adaptive 'fair value' price oscillates around."""
    x = logp[0]; P = 1.0
    level = np.empty(len(logp))
    for t in range(len(logp)):
        P += q; K = P / (P + r)
        x = x + K * (logp[t] - x); P = (1 - K) * P
        level[t] = x
    return level


def _deadband(target: np.ndarray, band: float) -> np.ndarray:
    """Hold the current position; only re-trade to a new target once it moves
    >= band. Suppresses the daily micro-rebalances (mostly from the continuous
    VIX risk-scaler) that would otherwise bleed away to transaction costs."""
    held = np.empty(len(target)); cur = 0.0
    for t in range(len(target)):
        if abs(target[t] - cur) >= band:
            cur = target[t]
        held[t] = cur
    return held


class KalmanTrendMR(Strategy):
    name = "kalman_trend_mr_blend"

    SPEEDS = [3e-9, 6e-9, 1.2e-8, 2.4e-8, 4e-8, 6e-8]  # multi-speed trend ensemble
    Q_LEVEL = 1e-5
    MR_Q = 1e-2          # level smoothing for the mean-reversion residual
    MR_ZWIN = 60         # rolling window for residual z-score
    W_TREND = 0.6        # blend weight: 0.6 trend / 0.4 mean-reversion
    VIX_Q_LEVEL = 2e-4   # Kalman on ^VIX: level / trend process noise
    VIX_Q_TREND = 2e-3
    VIX_CUT = 0.6        # max de-risking when implied vol is rising fast
    BAND = 0.15          # position deadband: re-trade only on moves > 15% notional

    def signal(self, prices: pd.DataFrame) -> pd.Series:
        c = prices["close"].astype(float)
        logp = np.log(c.values)

        # 1. Trend direction: fraction of Kalman speeds in an uptrend, in [0, 1].
        trend = np.mean([(_llt_trend(logp, self.Q_LEVEL, qt) > 0).astype(float)
                         for qt in self.SPEEDS], axis=0)

        # 2. Mean reversion: buy dips below the Kalman level, only in uptrends.
        resid = pd.Series(logp - _kalman_level(logp, self.MR_Q), index=c.index)
        z = (resid / resid.rolling(self.MR_ZWIN, min_periods=15).std()).bfill().values
        mr = np.clip(-z, 0.0, 1.0) * (trend > 0)
        blend = np.clip(self.W_TREND * trend + (1 - self.W_TREND) * mr, 0.0, 1.0)

        # 3. Risk overlay: de-risk when the Kalman implied-vol (VOL) slope is rising.
        vol = load_prices(VOL)["close"].reindex(c.index).ffill().bfill().values
        vslope = _llt_trend(vol, self.VIX_Q_LEVEL, self.VIX_Q_TREND, r=1.0)
        vstd = pd.Series(vslope, index=c.index).rolling(252, min_periods=60).std().bfill().values
        risk = 1.0 - self.VIX_CUT * np.clip(vslope / vstd, 0.0, 1.0)  # in [0.4, 1.0]

        # 4. Deadband to cut turnover (survive 1 bp/turn friction), then shift 1
        #    bar (trade next bar, no look-ahead).
        pos = _deadband(np.clip(blend * risk, 0.0, 1.0), self.BAND)
        return pd.Series(pos, index=c.index).shift(1).fillna(0.0)


def main() -> None:
    prices = load_prices(ASSET)
    sig = KalmanTrendMR().signal(prices).rename("position")
    sig.to_frame().to_parquet(SIGNAL_PATH)
    print(f"wrote {len(sig)} signals -> {SIGNAL_PATH}")


if __name__ == "__main__":
    main()
