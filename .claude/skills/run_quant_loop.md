---
description: Executes the Maker/Checker cycle autonomously to discover and validate trading signals.
---

## Instructions

1. **Review Current State**
   - Read `STATE.md` to understand the current objective.
   - Extract any previous lessons learned or mathematical flaws to avoid.
   - Note the target asset, success criteria (OOS Sharpe > 1.2, Max Drawdown ≤ 15%), and iteration count.

2. **Trigger Maker Agent**
   - Invoke the Maker to generate a trading signal or algorithmic strategy.
   - Provide context: current asset, market regime, and any previous failure logs.
   - Maker must produce:
     - Strategy code (in designated /maker directory)
     - Entry/exit logic
     - Position sizing rules
     - Expected logic rationale

3. **Trigger Checker Agent**
   - Invoke the Checker to execute the backtest on the Maker's output.
   - Checker evaluates:
     - Out-of-sample Sharpe ratio (target: > 1.2)
     - Maximum drawdown (target: ≤ 15%)
     - Hit rate and win/loss ratio
     - Robustness across market regimes
   - Checker outputs: `backtest_results.json` with all metrics and failure logs (if any).

4. **Evaluate Checker Results**
   - If **Checker FAILS** (OOS Sharpe ≤ 1.2 OR Max Drawdown > 15%):
     - Log the exact variance/failure reason in `STATE.md` (e.g., "over-fitted to 2020-2021 bull market")
     - Identify the mathematical flaw in Maker's logic
     - Mutate the Maker's underlying algorithm to fix the specific flaw
     - Output: `STATUS: RE-RUN`
     - **Return to step 2** (Maker-Checker loop repeats)
   
   - If **Checker SUCCEEDS** (OOS Sharpe > 1.2 AND Max Drawdown ≤ 15%):
     - Archive strategy and metrics to `/backtests`
     - Update `STATE.md` with final metrics and strategy summary
     - Output: `STATUS: ALPHA FOUND`
     - **Loop terminates** (alpha discovered)

5. **Maintain Isolation**
   - Maker never reads Checker output directly; only receives high-level failure descriptions.
   - Checker never inspects Maker code; only evaluates mathematical output (backtest results).
   - All communication flows through `STATE.md` and structured logs.

6. **Loop Until Success**
   - Repeat steps 2-4 autonomously until `STATUS: ALPHA FOUND` is achieved.
   - Track iteration count, timing, and strategy mutations in `architecture_decisions.log`.
