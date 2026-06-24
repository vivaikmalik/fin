"""Checker entrypoint. Reads ONLY the Result JSON (CLAUDE.md §5).

It must not import anything from maker.*. It judges the math and emits a
verdict the loop uses to decide PASS vs RE-RUN.
"""
from __future__ import annotations
import json
from shared.contract import Result, VERDICT_PATH, MIN_OOS_SHARPE, MAX_DRAWDOWN
from checker.metrics import sharpe, max_drawdown


def verify() -> dict:
    res = Result.load()  # reads backtest_results.json — the only input

    s = sharpe(res.oos_returns)
    dd = max_drawdown(res.equity_curve)
    passed = s >= MIN_OOS_SHARPE and dd <= MAX_DRAWDOWN

    reasons = []
    if s < MIN_OOS_SHARPE:
        reasons.append(f"OOS Sharpe {s:.2f} < {MIN_OOS_SHARPE}")
    if dd > MAX_DRAWDOWN:
        reasons.append(f"Max drawdown {dd:.1%} > {MAX_DRAWDOWN:.0%}")

    verdict = {
        "status": "ALPHA FOUND" if passed else "RE-RUN",
        "passed": passed,
        "oos_sharpe": round(s, 4),
        "max_drawdown": round(dd, 4),
        "n_bars": res.n_bars,
        "reasons": reasons,
    }
    with open(VERDICT_PATH, "w") as f:
        json.dump(verdict, f, indent=2)
    return verdict


if __name__ == "__main__":
    v = verify()
    print(json.dumps(v, indent=2))
