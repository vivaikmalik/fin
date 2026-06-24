"""Data contract — the ONLY coupling allowed between Maker and Checker.

Isolation rule (CLAUDE.md §5):
  Maker  -> writes a Signal  (target position per bar, in [-1, 1])
  Runner -> turns Signal + Prices into a Result (equity curve + OOS returns)
  Checker-> reads the Result ONLY. It never imports maker.* code.

Both sides depend on these schemas, nothing else.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import json

ASSET = "SPY"

# In-sample / out-of-sample split. Checker judges OOS only.
TRAIN_END = "2018-12-31"      # everything <= this is in-sample
# OOS = TRAIN_END .. present

# Success criteria (CLAUDE.md §6).
MIN_OOS_SHARPE = 1.2
MAX_DRAWDOWN = 0.15          # 15%

SIGNAL_PATH = "data/signals.parquet"          # produced by Maker
RESULT_PATH = "backtests/results/backtest_results.json"  # produced by Runner
VERDICT_PATH = "checker/verdict.json"         # produced by Checker


@dataclass
class Result:
    """Neutral mathematical output handed to the Checker.

    Contains NO reference to how the signal was generated.
    """
    asset: str
    train_end: str
    dates: list[str]          # OOS dates (ISO)
    oos_returns: list[float]  # per-bar strategy returns over OOS window
    equity_curve: list[float] # cumulative equity over OOS window
    n_bars: int
    meta: dict[str, Any]      # free-form: turnover, bars, etc. (no code)

    def save(self, path: str = RESULT_PATH) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @staticmethod
    def load(path: str = RESULT_PATH) -> "Result":
        with open(path) as f:
            return Result(**json.load(f))
