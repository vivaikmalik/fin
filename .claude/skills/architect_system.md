---
description: Designs the tech stack, creates the directory structure, and initializes the Maker/Checker environment for a high-performance quant system.
---

## Instructions

1. **Analyze Requirements**
   - Evaluate the quant system requirements (heavy matrix math, sub-second execution speed, backtesting at scale).
   - Assess data ingestion needs, alpha research complexity, and verification demands.

2. **Select Tech Stack**
   - Choose optimal languages for:
     - **Maker (Alpha Generator)**: Performance-critical signal generation (Python + NumPy/Pandas, or Rust for ultra-high-performance)
     - **Checker (Verifier)**: Risk metrics computation and out-of-sample validation (Python for accessibility, optional compiled components)
     - **Data Layer**: Efficient ingestion and storage (parquet, HDF5, or time-series DB)
   - Document rationale in `STATE.md`.

3. **Architecture Design**
   - Enforce strict Maker/Checker isolation using Git worktrees or separate processes.
   - The Checker must only evaluate mathematical outputs (backtest results, Sharpe ratio, max drawdown), never inspect Maker code.
   - Define success criteria: OOS Sharpe ≥ 1.2, Max Drawdown ≤ 15%, valid asset coverage.

4. **Create Directory Structure**
   Execute commands to establish:
   ```
   /maker              - Alpha generation strategies
   /checker            - Risk verification & metrics
   /data               - Input datasets and caches
   /backtests          - Backtest execution & results
   /logs               - Execution and failure logs
   /architecture_decisions.log - Stack decisions & rationale
   /STATE.md           - Current system state
   ```

5. **Initialize Environments**
   - Create Git worktrees for isolated Maker/Checker development (if Git repo exists).
   - Generate placeholder files for strategy templates, verifier scripts, and config files.
   - Set up logging and output directories.

6. **Document & Output**
   - Write all architectural decisions to `architecture_decisions.log`.
   - Output: `STATUS: ARCHITECTURE COMPLETE`
