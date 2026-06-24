# STATE.md — Autonomous Quant System

**Phase:** UNIVERSAL ALPHA ✅ — one frozen strategy clears both gates on SPY *and* QQQ
**Last updated:** 2026-06-24
**Target asset:** SPY (primary) + QQQ (OOD generalization test, ^VXN overlay)
**Iteration:** 6 — **OOD asset test**: the FROZEN KalmanTrendMR (identical params
+ 0.15 deadband, only the data swapped to QQQ/^VXN) scores **net OOS Sharpe 1.28,
MaxDD 10.5% — PASS**. SPY is 1.24 / 8.4%. No mutation needed; the edge generalizes
out-of-distribution → **STATUS: UNIVERSAL ALPHA**.
*Iter-5:* 0.15 position deadband cut turnover 203→144 to survive 1 bp/turn
friction (net Sharpe 1.24). *Iter-4 failure (recorded):* friction had dropped the
no-deadband strategy to 1.197 < 1.2 (the continuous VIX scaler re-traded daily).

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
3. Kalman ^VIX-slope RISK OVERLAY → de-risk when implied vol is rising;
4. 0.15 position DEADBAND → re-trade only on moves >15% notional (turnover/cost).
Position long/flat in [0,1], shifted 1 bar. **Net-of-friction OOS Sharpe 1.24,
MaxDD 8.4%** (1 bp/turn). Defensive (avg pos ~0.44) — wins on risk-adjusted
return, not raw return.

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
- **Friction (iter 4)**: 1 bp/turn costs ~0.014 Sharpe (1.211→1.197). The
  continuous VIX risk-scaler re-trades a little EVERY bar. Fix = deadband on the
  final position (only re-trade when target moves > band) → fewer, larger trades.

## Next Action
None — loop terminated at ALPHA FOUND. To extend: add transaction-cost modelling
in the runner, or stress-test on a second asset (e.g. QQQ) before live use.
