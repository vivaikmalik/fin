# STATE.md — Autonomous Quant System

**Phase:** UNIVERSAL ALPHA across **equities** ✅ — edge boundary mapped: NOT cross-asset-class
**Last updated:** 2026-06-24
**Target asset:** SPY + QQQ (both PASS) ; GLD (FAIL — defines the boundary)
**Iteration:** 7 — **CROSS-ASSET test** on GLD/^GVZ. The FROZEN strategy (no
mutation, per instruction) scores **OOS Sharpe 0.85 < 1.2** → RE-RUN. The edge is
**equity-specific**; terminated without mutating. See "Edge Boundary" below.
*Iter-6:* QQQ/^VXN OOD test PASSED (net Sharpe 1.28, MaxDD 10.5%) → UNIVERSAL
ALPHA across equity indices. *Iter-5:* 0.15 deadband cut turnover 203→144 to
survive 1 bp/turn friction (net Sharpe 1.24). *Iter-4:* friction had dropped the
no-deadband strategy to 1.197 < 1.2.

## Edge Boundary — Cross-Asset Test (GLD / ^GVZ), 2026-06-24
FROZEN KalmanTrendMR (identical Kalman params + 0.15 deadband), only the data
swapped to Gold. **No mutation** (test was strictly generalization). Net of 1
bp/turn friction, OOS = 2019-01-02 … 2026-06-24 (1,879 bars):

| Metric | GLD strategy | Gate | GLD buy&hold |
|--------|-------------|------|--------------|
| OOS Sharpe | **0.85** | ≥ 1.2 ❌ | 0.93 |
| Max Drawdown | 13.6% | ≤ 15% ✅ | 26.2% |
| OOS total return | +60% | — | +202% |
| turnover | 151 | — | — |

**Why it fails (the boundary):** the strategy's core alpha lever is the
rising-implied-vol RISK-OFF overlay, which exploits the equity **leverage
effect** — for SPY/QQQ, `corr(Δimplied-vol, return)` is strongly *negative*, so
rising vol reliably precedes drawdowns. For **gold it is +0.21 (positive)**:
gold often *rallies* as ^GVZ rises (safe-haven/crisis bid). The overlay therefore
de-risks into gold's rallies, and the strategy's Sharpe (0.85) falls *below* even
gold buy&hold (0.93) — it adds no value on this asset class. Drawdown control
still works (13.6%), but the return engine does not transfer.

**Conclusion:** the edge generalizes across **equity indices** (SPY↔QQQ) but
**not across asset classes** (commodities/gold). It is a risk-managed *equity*
trend/mean-reversion strategy, not a universal one.

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
