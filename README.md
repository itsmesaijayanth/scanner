# NSE Nifty 50 Scraper

Downloads NSE historical trade data JSON for all configured Nifty 50 symbols.

The scraper does not use pasted cookies. Each run warms up a fresh NSE session, calls the historical quote API, and stores one JSON file per symbol.

By default it stores only the latest trading-day object from NSE. Window mode is still available when you want to save a larger response later.

## Data Layout

```text
data/raw/SYMBOL/YYYY/Mon/DD/response.json
data/runs/DD-MM-YYYY.json
```

Example:

```text
data/raw/SBIN/2026/Aug/26/response.json
data/raw/RELIANCE/2026/Aug/26/response.json
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

## Tests

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Daily GitHub Action

The workflow at `.github/workflows/daily-nse-fetch.yml` runs every day at 4:30 PM IST.

GitHub Actions cron uses UTC, so the schedule is:

```yaml
cron: "0 11 * * *"
```

The workflow:

1. Installs dependencies with `uv`.
2. Runs tests.
3. Fetches daily latest-trading-day data for all configured symbols.
4. Commits changed files under `data/`.
5. Pushes the commit back to the same branch.

The repository needs this permission in the workflow:

```yaml
permissions:
  contents: write
```
