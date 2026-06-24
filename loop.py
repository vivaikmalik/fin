"""Orchestrator. Runs Maker -> Runner -> Checker as isolated subprocesses.

Process isolation (CLAUDE.md §5): each stage is a separate Python process.
The Checker subprocess only ever reads backtest_results.json; it shares no
memory or imports with the Maker.
"""
from __future__ import annotations
import subprocess
import sys
import json
from shared.contract import VERDICT_PATH

STAGES = [
    [sys.executable, "-m", "maker.generate_signal"],
    [sys.executable, "-m", "backtests.runner"],
    [sys.executable, "-m", "checker.verify"],
]


def run_once() -> dict:
    for cmd in STAGES:
        subprocess.run(cmd, check=True)
    with open(VERDICT_PATH) as f:
        return json.load(f)


if __name__ == "__main__":
    verdict = run_once()
    print(json.dumps(verdict, indent=2))
    sys.exit(0 if verdict["passed"] else 1)
