# NSE Nifty 50 Scraper

Downloads NSE historical trade data JSON for all configured Nifty 50 symbols.

The scraper does not use pasted cookies. Each run warms up a fresh NSE session, calls the historical quote API, and stores one JSON file per symbol.

By default it stores only the latest trading-day object from NSE. Window mode is still available when you want to save a larger response later.

## Data Layout

```text
data/raw/SYMBOL/YYYY/Mon/DD/response.json
data/algo/swing_momentum/SYMBOL/YYYY/Mon/DD/window/response.json
data/runs/DD-MM-YYYY.json
```

Example:

```text
data/raw/SBIN/2026/Aug/26/response.json
data/raw/RELIANCE/2026/Aug/26/response.json
data/algo/swing_momentum/SBIN/2026/Aug/26/window/response.json
data/runs/26-08-2026.json
```

## Setup

```bash
uv sync
```

## Run All Nifty 50 Symbols

Fetch the latest trading-day data for every configured symbol:

```bash
uv run nse-fetch
```

The default daily mode uses a short 7-day lookback and stores only the newest row by NSE's `mtimestamp`. This keeps holidays/weekends from creating empty holiday folders.

Save the full response for an explicit window:

```bash
uv run nse-fetch --mode window --from-date 26-07-2026 --to-date 26-08-2026
```

## Run Selected Symbols

```bash
uv run nse-fetch --symbols SBIN,RELIANCE,TCS
```

## Seed Historical Data

Seed roughly 5 years in 90-day chunks:

```bash
uv run nse-seed-history --years 5 --chunk-days 90
```

Seed selected symbols first while testing:

```bash
uv run nse-seed-history --symbols SBIN,TCS --years 1 --chunk-days 90
```

## Run Swing Momentum Algorithm

Run the 30-calendar-day swing momentum algorithm for all configured symbols:

```bash
uv run swing-momentum
```

Run selected symbols:

```bash
uv run swing-momentum --symbols SBIN,RELIANCE,TCS
```

Run for an explicit window end date:

```bash
uv run swing-momentum --end-date 02-09-2026 --window-days 30
```

Backfill all trading dates from seeded raw data (skips existing outputs by default):

```bash
uv run swing-momentum --backfill --window-days 30
```

Limit a backfill range or force recomputation:

```bash
uv run swing-momentum --backfill --from-date 01-01-2024 --to-date 31-12-2024
uv run swing-momentum --backfill --no-resume
```

The algorithm reads `data/raw/`, uses the latest available trading day when the requested end date is a holiday, and writes one analysis file per symbol under `data/algo/swing_momentum/`.

## Tests

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Daily GitHub Action

The workflow at `.github/workflows/daily-nse-pipeline.yml` runs every day at 4:30 PM IST.

GitHub Actions cron uses UTC, so the schedule is:

```yaml
cron: "0 11 * * *"
```

The workflow:

1. Installs dependencies with `uv`.
2. Fetches daily latest-trading-day data for all configured symbols.
3. Commits changed files under `data/raw` and `data/runs`.
4. Runs the swing momentum algorithm for all configured symbols.
5. Commits changed files under `data/algo` and `data/runs`.
6. Pushes each commit back to the same branch.

The repository needs this permission in the workflow:

```yaml
permissions:
  contents: write
```
