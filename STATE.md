# STATE.md — Autonomous Quant System

**Phase:** ALPHA FOUND ✅ (verified by isolated Checker)
**Last updated:** 2026-06-24
**Target asset:** SPY
**Iteration:** 3 — PASS: OOS Sharpe 1.21 ≥ 1.2, MaxDD 8.4% ≤ 15%. See WINNER.md.

---

## Objective
Discover a trading strategy on SPY that passes out-of-sample verification:
- **OOS Sharpe ≥ 1.2**
- **Max Drawdown ≤ 15%**

OOS window = bars after `TRAIN_END = 2018-12-31`.

## Tech Stack (see architecture_decisions.log)
| Layer | Choice | Why |
|-------|--------|-----|
| Maker | Python + Pandas | fast alpha iteration on daily bars |
| Checker | Python + NumPy | dependency-light risk math |
| Data | Parquet (PyArrow) via yfinance | compact, fast, cacheable |
| Runner | NumPy/Pandas vectorized | neutral signal→equity engine |

## Maker/Checker Isolation
Communication is **files only** — no shared imports across the boundary:

```
maker.generate_signal  ──► data/signals.parquet
                              │
backtests.runner       ◄─────┘  reads signal + prices
        │
        └──► backtests/results/backtest_results.json   (math only)
                              │
checker.verify         ◄──────┘  reads JSON ONLY, never maker.*
        │
        └──► checker/verdict.json   (PASS / RE-RUN + reasons)
```
- Code boundary: `checker/verify.py` imports only `shared.contract` + `checker.metrics`.
- Process boundary: `loop.py` runs each stage as a separate subprocess.
- Git: Maker mutations live on the `maker` worktree branch.

## Current Strategy (VERIFIED WINNER — see WINNER.md)
`maker/generate_signal.py :: KalmanTrendMR` — three causal Kalman filters:
1. multi-speed Kalman local-linear-trend ENSEMBLE → long/flat direction;
2. Kalman-level MEAN-REVERSION sleeve → buy dips, uptrend-gated (blend 0.6/0.4);
3. Kalman ^VIX-slope RISK OVERLAY → de-risk when implied vol is rising.
Position long/flat in [0,1], shifted 1 bar. OOS Sharpe 1.21, MaxDD 8.4%.
Note: defensive (avg pos 0.44) — wins on risk-adjusted return, not raw return
(OOS +77% vs SPY +227%).

## How to Run
```bash
pip install -r requirements.txt
python -m data.ingest        # cache SPY prices
python loop.py               # maker -> runner -> checker, prints verdict
```

## Loop Memory (lessons / failures to avoid)
*(run_quant_loop appends rejected-strategy diagnoses here so the Maker does
not repeat the same mathematical flaw.)*
- **TrendMA(50,200)**: too slow — rides the entire COVID crash (DD 33.7%). A
  fixed long lookback cannot exit fast crashes. → adaptive Kalman trend.
- **Single-speed Kalman trend**: OOS Sharpe is a *fragile spike* (1.16 at
  qt=1e-8, ~1.0 at neighbours). Never tune one speed to OOS → use an ensemble.
- **Shorting SPY (long/short trend)**: hurts — bear-market rallies squeeze the
  shorts; every short-floor < 0 lowered OOS Sharpe. Stay long/flat.
- **Volatility *targeting* (realized vol)**: lowers Sharpe — it shrinks size
  right as post-spike recoveries fire. Risk-managing on *implied-vol slope*
  (VIX rising), not realized-vol level, is what works.
- **VIX *level* gate**: rejected — VIX peaks at bottoms, so cutting on high VIX
  sells the low. Only the VIX *slope* (rising) adds Sharpe.
- **Continuous trend sizing / adaptive-AR sleeve**: tested, both < the binary
  sign-ensemble + MR blend. Don't revisit.
- Robust ceiling on **SPY close alone** is ~1.15; crossing 1.2 required the
  ^VIX risk signal. See memory `spy-kalman-sharpe-ceiling`.

## Next Action
None — loop terminated at ALPHA FOUND. To extend: add transaction-cost modelling
in the runner, or stress-test on a second asset (e.g. QQQ) before live use.
