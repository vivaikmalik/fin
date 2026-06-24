---
description: Fetches raw daily or hourly standard equity data and formats it for the Maker agent without any preprocessing or feature engineering.
---

## Instructions

1. **Select Data Source**
   - Use `yfinance` library (or equivalent in your chosen Python stack as defined in STATE.md).
   - Ensure the library is installed and accessible in your Maker environment.

2. **Download Historical Data**
   - Fetch data for ticker: `SPY` (S&P 500 ETF, proxy for broad market).
   - Time range: Exactly 5 years of historical daily data (from today minus 5 years to today).
   - Data fields required:
     - Open (O)
     - High (H)
     - Low (L)
     - Close (C)
     - Volume (V)
     - Adjusted Close (Adj Close) if available
   - Frequency: Daily bars
   - Ensure no missing data; fill gaps or interpolate if necessary (forward-fill or drop NaN rows).

3. **Raw Data Only**
   - Perform **zero feature engineering**.
   - No normalization, scaling, or preprocessing.
   - No technical indicators (moving averages, RSI, MACD, etc.).
   - No derived features (returns, log-returns, volatility windows, etc.).
   - Your only job is ingestion and minimal validation.

4. **Format & Validate**
   - Convert to Pandas DataFrame with columns: `[Date, Open, High, Low, Close, Volume]`.
   - Ensure Date column is datetime type and sorted chronologically (oldest to newest).
   - Verify row count is approximately 252 * 5 = 1,260 trading days (±5 days for holidays/weekends).
   - Check for null values and log any gaps or anomalies.

5. **Save to Shared State**
   - Serialize the raw dataframe to Parquet format.
   - Save to: `shared_state/latest_data.parquet` (or the data directory path as defined in `STATE.md`).
   - Parquet format ensures efficient storage and fast read access for the Maker.
   - Verify file was created and is readable.

6. **Output Status**
   - On successful completion: `STATUS: DATA READY`
   - Log the data shape (rows, columns), date range, and any warnings to stdout.
   - If failure: Log the error and output `STATUS: DATA INGESTION FAILED`
