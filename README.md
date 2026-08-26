# NSE Nifty 50 Scraper

Downloads NSE historical trade data JSON for all configured Nifty 50 symbols.

The scraper does not use pasted cookies. Each run warms up a fresh NSE session, calls the historical quote API, and stores one JSON file per symbol.

## Data Layout

```text
data/raw/SYMBOL/DD-MM-YYYY/response.json
data/runs/DD-MM-YYYY.json
```

Example:

```text
data/raw/SBIN/26-08-2026/response.json
data/raw/RELIANCE/26-08-2026/response.json
data/runs/26-08-2026.json
```

## Setup

```bash
uv sync
```

## Run All Nifty 50 Symbols

Fetch the default rolling 30-day window:

```bash
uv run nse-fetch
```

Fetch an explicit 30-day window:

```bash
uv run nse-fetch --from-date 26-07-2026 --to-date 26-08-2026
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
3. Fetches the rolling 30-day window for all configured symbols.
4. Commits changed files under `data/`.
5. Pushes the commit back to the same branch.

The repository needs this permission in the workflow:

```yaml
permissions:
  contents: write
```
