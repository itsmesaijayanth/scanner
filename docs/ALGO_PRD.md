# Short Term Trading Algorithm PRD

## 1. Goal

Add a separate algorithm module that reads stored NSE daily JSON data and produces a per-symbol 30-calendar-day swing momentum analysis.

The algorithm output should explain what is happening inside the selected date-wise window: trend direction, monthly high/low, where those extremes happened, signal days, target zone, stop-loss reference, and enough supporting detail to debug or backtest the decision later.

This feature is for analysis/backtesting and workflow automation. It should not place trades or present output as financial advice.

## 2. Current Data Assumption

The scraper stores daily NSE objects in this format:

```text
data/raw/{SYMBOL}/YYYY/Mon/DD/response.json
```

Example:

```text
data/raw/SBIN/2026/Sep/01/response.json
```

Each `response.json` contains one daily NSE object:

```json
{
  "chOpeningPrice": 1711.9,
  "chTradeHighPrice": 1719.7,
  "chTradeLowPrice": 1690.5,
  "chClosingPrice": 1691.5,
  "chSymbol": "ADANIPORTS",
  "mtimestamp": "26-Aug-2026"
}
```

The algorithm must use the NSE `mtimestamp` as the trading date, not the folder date alone.

## 3. New Folder Structure

Add a separate algorithm package and output folder:

```text
scanner/
  src/
    nse_nifty50_scraper/
      algo/
        __init__.py
        models.py
        loader.py
        swing_momentum.py
        runner.py
        cli.py
  data/
    algo/
      swing_momentum/
        {SYMBOL}/
          YYYY/
            Mon/
              DD/
                window/
                  response.json
  tests/
    algo/
      test_loader.py
      test_swing_momentum.py
      test_algo_paths.py
  .github/
    workflows/
      daily-swing-momentum.yml
```

## 4. Output Path

For each symbol and each analysis date:

```text
data/algo/swing_momentum/{SYMBOL}/YYYY/Mon/DD/window/response.json
```

Example:

```text
data/algo/swing_momentum/SBIN/2026/Sep/02/window/response.json
```

The date path is the algorithm run's window end date. If the run happens on a holiday, the end date should become the latest available trading date in the local data, not a holiday date with no market row.

## 5. Seeding Historical Data

Before useful backtesting, we need to seed older daily data.

Implementation plan:

1. Add a seeding command that requests historical windows from NSE.
2. Store each returned row using the daily storage format:

```text
data/raw/{SYMBOL}/YYYY/Mon/DD/response.json
```

3. Probe NSE's allowed historical range safely:
   - Start with 1 year.
   - Then 3 years.
   - Then 5 years.
   - If NSE rejects a larger window, fall back to chunked requests.
4. Prefer chunking by smaller windows, such as 90 days or 180 days, to reduce API failures.
5. Deduplicate by symbol and `mtimestamp`; overwriting the same daily file is allowed.

Recommended seeding command:

```bash
uv run nse-seed-history --years 5 --chunk-days 90
```

If the API supports more than 5 years reliably, we can extend the seed later.

## 6. Trading Terms

For a selected symbol and 30-calendar-day window:

- Window Period: all available trading rows where `start_date <= mtimestamp <= end_date`.
- Open: `chOpeningPrice`.
- High: `chTradeHighPrice`.
- Low: `chTradeLowPrice`.
- Close: `chClosingPrice`.
- Monthly High: maximum `chTradeHighPrice` inside the window.
- Monthly Low: minimum `chTradeLowPrice` inside the window.
- Current Day: latest trading row inside the window.
- UpTrend: Monthly Low is closer to Current Day than Monthly High.
- DownTrend: Monthly High is closer to Current Day than Monthly Low.

Distance is measured in trading rows, not calendar days. This avoids weekend and holiday gaps distorting the trend.

## 7. Tie Rules

The algorithm must be deterministic.

If Monthly High occurs more than once:

- Use the latest occurrence for trend distance.

If Monthly Low occurs more than once:

- Use the latest occurrence for trend distance.

If Monthly High and Monthly Low are equally close to Current Day:

- Return `trend = "Sideways"` unless a strong signal exists on the current day.
- If a current-day up signal exists, return `trend = "UpTrend"`.
- If a current-day down signal exists, return `trend = "DownTrend"`.
- If both signals somehow exist, return `trend = "Sideways"` and mark the signal as conflicting.

## 8. Signal Rules

Primary signals:

- Downtrend confirmation: `open == high`.
- Uptrend confirmation: `open == low`.

Because NSE values are floats, exact equality should use a tiny tolerance:

```text
abs(open - high) <= 0.01
abs(open - low) <= 0.01
```

Signal strength:

- `strong`: signal appears on the latest trading day.
- `recent`: signal appears within the last 3 trading rows.
- `weak`: signal appears earlier inside the window.
- `none`: no matching signal.

Signal direction:

- `bearish_momentum`: open equals high.
- `bullish_momentum`: open equals low.

## 9. Algorithm Logic

Input:

- symbol
- 30-calendar-day start date
- end date
- daily rows for that symbol

Steps:

1. Load all daily rows for symbol.
2. Parse `mtimestamp` into dates.
3. Filter rows to the calendar window.
4. Sort rows oldest to newest by trading date.
5. Identify Monthly High row.
6. Identify Monthly Low row.
7. Identify Current Day row.
8. Calculate distance from Monthly High to Current Day in trading rows.
9. Calculate distance from Monthly Low to Current Day in trading rows.
10. Determine trend:
    - if high distance < low distance: `DownTrend`
    - if low distance < high distance: `UpTrend`
    - otherwise apply tie rules
11. Determine expected next zone:
    - `UpTrend`: expected move toward Monthly High
    - `DownTrend`: expected move toward Monthly Low
    - `Sideways`: no directional target
12. Evaluate momentum signals.
13. Produce JSON response with full supporting evidence.

## 10. Output JSON Contract

Each algorithm output file should contain:

```json
{
  "algorithm": "swing_momentum",
  "version": "0.1.0",
  "symbol": "SBIN",
  "window": {
    "start_date": "03-08-2026",
    "end_date": "01-09-2026",
    "calendar_days": 30,
    "trading_rows": 21
  },
  "trend": {
    "direction": "DownTrend",
    "reason": "monthly_high_is_closer_to_current_day",
    "monthly_high": {
      "date": "28-08-2026",
      "price": 1080.5,
      "distance_to_current_trading_rows": 2
    },
    "monthly_low": {
      "date": "05-08-2026",
      "price": 1010.2,
      "distance_to_current_trading_rows": 18
    },
    "current": {
      "date": "01-09-2026",
      "open": 1051.3,
      "high": 1051.3,
      "low": 1027.1,
      "close": 1034.5
    }
  },
  "signals": {
    "active_signal": "bearish_momentum",
    "strength": "strong",
    "events": [
      {
        "date": "01-09-2026",
        "type": "bearish_momentum",
        "rule": "open_equals_high",
        "open": 1051.3,
        "high": 1051.3
      }
    ]
  },
  "levels": {
    "target_reference": {
      "label": "monthly_low",
      "price": 1010.2
    },
    "opposite_extreme": {
      "label": "monthly_high",
      "price": 1080.5
    },
    "risk_reference": {
      "label": "opposite_extreme",
      "price": 1080.5
    }
  },
  "verdict": {
    "state": "confirmed_downtrend",
    "confidence": "medium",
    "notes": [
      "Trend is down because monthly high is closer to current day.",
      "Current day has bearish momentum because open equals high."
    ]
  },
  "source_rows": [
    {
      "date": "01-09-2026",
      "open": 1051.3,
      "high": 1051.3,
      "low": 1027.1,
      "close": 1034.5
    }
  ]
}
```

The `source_rows` array should include the compact OHLC rows used by the algorithm. That makes every output auditable.

## 11. CLI Design

Run algorithm for all symbols using the latest available date:

```bash
uv run swing-momentum
```

Run for selected symbols:

```bash
uv run swing-momentum --symbols SBIN,RELIANCE,TCS
```

Run for an explicit window end date:

```bash
uv run swing-momentum --end-date 02-09-2026 --window-days 30
```

Run seeding:

```bash
uv run nse-seed-history --years 5 --chunk-days 90
```

## 12. Daily Workflow

Add a second workflow:

```text
.github/workflows/daily-swing-momentum.yml
```

Workflow behavior:

1. Check out repo.
2. Install uv.
3. Sync dependencies.
4. Run scraper daily mode to fetch latest NSE rows.
5. Run swing momentum algorithm for all symbols with a 30-calendar-day window.
6. Commit changed data under:

```text
data/raw/
data/runs/
data/algo/
```

7. Push back to the same branch.

Recommended schedule:

- Run after market data fetch has had time to complete.
- If NSE fetch runs at 4:30 PM IST, run algorithm at 4:45 PM IST.

GitHub cron:

```yaml
cron: "15 11 * * *"
```

This is 4:45 PM IST because GitHub cron is UTC.

## 13. Backtesting Plan

After seeding:

1. Build a backtest runner that walks every symbol day by day.
2. For each trading date, construct a 30-calendar-day lookback window.
3. Run the same swing momentum logic.
4. Save or summarize:
   - trend distribution
   - signal frequency
   - next-day and next-N-day outcomes
   - target hit rate
   - stop-loss hit rate
   - conflicting/sideways cases

Backtesting must use only data available up to that date. It must not look ahead.

## 14. Edge Cases

- Fewer than 2 rows in window: return `insufficient_data`.
- Missing OHLC fields: return symbol failure in run summary.
- Missing `mtimestamp`: ignore that row and report it in diagnostics.
- Duplicate date rows: keep the latest file on disk; within loaded rows, keep one row per date.
- Holiday run: use latest available trading date for analysis output path.
- Equal high/low distance: use tie rules.
- Both open-high and open-low true: mark conflicting signal.

## 15. Implementation Phases

Phase 1: Historical seeding

- Add seed command.
- Fetch chunked history.
- Store each daily row in `data/raw/{SYMBOL}/YYYY/Mon/DD/response.json`.

Phase 2: Algorithm engine

- Add data loader.
- Add swing momentum calculator.
- Add JSON output writer.
- Add tests with deterministic sample rows.

Phase 3: CLI and workflow

- Add `swing-momentum` command.
- Add daily algorithm workflow.
- Update README.

Phase 4: Backtesting

- Add backtest runner.
- Run across seeded data.
- Add aggregate report outputs.

## 16. Open Decisions

Recommended defaults:

- Daily algorithm window: 30 calendar days.
- Trend distance: trading-row distance.
- Equality tolerance: 0.01.
- Output path date: latest available trading date in the selected window.
- Algorithm workflow time: 4:45 PM IST.

Need confirmation before implementation:

1. Should the algorithm workflow also run the NSE fetch first, or only use already-fetched data?
2. Should seeding try exactly 5 years first, or should we probe until NSE stops accepting older dates?
3. Should old data remain tracked in Git, or should seeded historical data be kept outside Git because it may become large?
