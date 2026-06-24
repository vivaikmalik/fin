# STATE.md — Autonomous Quant System

**Phase:** ARCHITECTURE COMPLETE
**Last updated:** 2026-06-24
**Target asset:** SPY
**Iteration:** 0 (baseline scaffold, not yet verified)

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

## Current Strategy (baseline placeholder)
`maker/generate_signal.py :: TrendMA(fast=50, slow=200)` — long SPY when
50d MA > 200d MA, flat otherwise. Signal shifted 1 bar (no look-ahead).
Not yet validated; exists so the loop runs end-to-end.

## How to Run
```bash
pip install -r requirements.txt
python -m data.ingest        # cache SPY prices
python loop.py               # maker -> runner -> checker, prints verdict
```

## Loop Memory (lessons / failures to avoid)
*(run_quant_loop appends rejected-strategy diagnoses here so the Maker does
not repeat the same mathematical flaw.)*
- (none yet)

## Next Action
Run `run_quant_loop` to begin the Maker/Checker discovery cycle.
