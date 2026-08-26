# NSE Nifty 50 Historical Data Scraper PRD

## 1. Goal

Build a small Python repository that downloads a rolling 30-day window of historical trade data for all Nifty 50 companies from NSE's internal quote API and stores the raw JSON responses in a predictable folder structure.

The scraper must not depend on pasted cookies. It should create a fresh NSE browser-like session each run, collect current cookies, call the API for every configured symbol, save the JSON data, and commit/push the new daily data from GitHub Actions.

## 2. What We Are Building

A `uv`-managed Python project with:

- A reusable NSE client.
- A Nifty 50 symbol configuration file.
- A command-line scraper.
- Structured JSON output by symbol and run date.
- Basic tests for date handling, path generation, and response saving.
- A GitHub Actions workflow that runs every day at 4:30 PM India time and pushes newly downloaded data back to the repository.

## 3. Non-Goals

- No database in the first version.
- No CSV conversion in the first version.
- No trading logic, alerts, charts, or analytics yet.
- No hard-coded cookies, browser cookie export, or manual cookie refresh.
- No paid NSE data feed integration.

## 4. Data Source

The current target API pattern is:

```text
https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getHistoricalTradeData&symbol=SBIN&series=EQ&fromDate=26-07-2026&toDate=26-08-2026&csv=true
```

Even with `csv=true`, NSE may return JSON. For version 1, we store the raw JSON response exactly as returned.

Before calling the API, the scraper will visit:

```text
https://www.nseindia.com
https://www.nseindia.com/get-quote/equity/{SYMBOL}/{SLUG}
```

This warms up the session and lets NSE set short-lived cookies.

## 5. Scheduling

User requested: daily at `4:30 PM`.

GitHub Actions cron uses UTC, not local time. Assuming `4:30 PM Asia/Kolkata`, the workflow cron should be:

```yaml
cron: "0 11 * * *"
```

That runs at 11:00 UTC, which is 4:30 PM IST.

The workflow should also support manual runs through `workflow_dispatch`.

## 6. Packages

Runtime packages:

- `httpx`: HTTP client with session cookies, timeouts, retries-friendly API, and clean headers.
- `pydantic`: Validate settings/config shape and prevent bad symbol entries.
- `typer`: Clean command-line interface.
- `python-dateutil`: Date helpers if we add rolling date windows later.

Development packages:

- `pytest`: Tests.
- `ruff`: Linting and formatting.

Package manager:

- `uv`: Project setup, dependency lock, local runs, and GitHub Actions execution.

GitHub Actions:

- `actions/checkout`: Check out the repo.
- `astral-sh/setup-uv`: Install uv in the runner.

Current references checked:

- Astral recommends `astral-sh/setup-uv` for GitHub Actions.
- Astral docs show pinned examples for `actions/checkout` and `astral-sh/setup-uv`.

## 7. Proposed Folder Structure

```text
nse-nifty50-scraper/
  README.md
  pyproject.toml
  uv.lock
  .gitignore
  .github/
    workflows/
      daily-nse-fetch.yml
  config/
    nifty50.json
  data/
    raw/
      .gitkeep
    runs/
      .gitkeep
  docs/
    PRD.md
  src/
    nse_nifty50_scraper/
      __init__.py
      cli.py
      config.py
      dates.py
      nse_client.py
      paths.py
      runner.py
  tests/
    test_config.py
    test_dates.py
    test_paths.py
    test_runner.py
```

## 8. Data Output Structure

For each run:

```text
data/raw/{SYMBOL}/DD-MM-YYYY/response.json
```

Example:

```text
data/raw/SBIN/26-08-2026/response.json
data/raw/RELIANCE/26-08-2026/response.json
data/raw/TCS/26-08-2026/response.json
```

Each file stores one symbol's raw NSE response.

Possible optional metadata file:

```text
data/runs/DD-MM-YYYY.json
```

This can store:

- run date
- requested from/to dates
- number of symbols attempted
- number succeeded
- number failed
- failed symbols and error messages

## 9. CLI Design

Primary command:

```bash
uv run nse-fetch --from-date 26-07-2026 --to-date 26-08-2026
```

Useful options:

```bash
uv run nse-fetch --symbols SBIN,TCS,RELIANCE --from-date 26-07-2026 --to-date 26-08-2026
uv run nse-fetch --days 30
uv run nse-fetch --output-dir data/raw
```

Default behavior:

- If no symbol is provided, fetch all symbols from `config/nifty50.json`.
- If explicit dates are provided, use them.
- If no dates are provided, use the last 30 calendar days ending today.
- Save output under `data/raw/{symbol}/{run_date}/response.json`.

## 10. Nifty 50 Config Format

```json
[
  {
    "symbol": "SBIN",
    "series": "EQ",
    "company_name": "State Bank of India",
    "industry": "Financial Services",
    "isin": "INE062A01020"
  }
]
```

The scraper can use an optional `slug` when present. If it is not present, it generates a warm-up slug from the company name. If that quote page warm-up fails, it continues with homepage cookies and still calls the API.

## 11. GitHub Action Behavior

Workflow:

1. Run daily at 4:30 PM IST.
2. Check out repo with write credentials.
3. Install uv.
4. Sync dependencies.
5. Run tests.
6. Run scraper for all configured symbols.
7. Commit changed files under `data/raw/` and `data/runs/`.
8. Push commit back to the same branch.

Commit message:

```text
chore(data): fetch NSE data for YYYY-MM-DD
```

Permissions needed:

```yaml
permissions:
  contents: write
```

## 12. Reliability Rules

- Use one HTTP client session per scraper run.
- Warm up NSE cookies before API calls.
- Use browser-like headers.
- Add a small delay between symbol requests.
- Retry failed symbol calls a small number of times.
- Continue scraping other symbols if one symbol fails.
- Write a run summary so failures are visible.
- Never commit if no data changed.

## 13. Error Handling

For each symbol:

- If NSE returns HTTP error, log it and mark the symbol failed.
- If response is not JSON, save a short error in `_run.json` and do not save that symbol file.
- If a symbol fails after retries, continue with the next symbol.

The GitHub Action should fail only when:

- Most or all symbols fail.
- Config is invalid.
- Tests fail.
- Git push fails.

## 14. Implementation Plan

Step 1:

- Create `pyproject.toml` using uv.
- Add source package and CLI entrypoint.
- Add Nifty 50 config.

Step 2:

- Implement NSE client from the working sample.
- Replace `urllib` with `httpx` for cleaner sessions and timeouts.
- Store raw JSON.

Step 3:

- Implement runner for all symbols.
- Add retries, delay, and `_run.json`.

Step 4:

- Add tests for config, dates, paths, and save behavior.

Step 5:

- Add GitHub Actions daily cron workflow.
- Add README with local and GitHub setup instructions.

## 15. Open Questions Before Implementation

1. Daily run should fetch a rolling 30-day window.
2. Data will be committed into the same repository by GitHub Actions.
3. Store one JSON file per symbol using `SYMBOL/DD-MM-YYYY/response.json`.

Implementation default:

- Fetch last 30 calendar days every day.
- Commit to the same branch.
- Store one JSON file per symbol plus `data/runs/DD-MM-YYYY.json`.
