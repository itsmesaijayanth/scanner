from __future__ import annotations

import datetime as dt
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nse_nifty50_scraper.config import SymbolConfig
from nse_nifty50_scraper.dates import format_nse_date, parse_nse_timestamp
from nse_nifty50_scraper.db.persist import (
    persist_daily_bar,
    persist_run_summary,
    persist_window_response,
)
from nse_nifty50_scraper.nse_client import NSEClient, NSEClientError
from nse_nifty50_scraper.paths import run_summary_path


@dataclass
class SymbolResult:
    symbol: str
    status: str
    path: str | None = None
    trade_date: str | None = None
    error: str | None = None


@dataclass
class RunResult:
    mode: str
    run_date: str
    from_date: str
    to_date: str
    attempted: int
    succeeded: int
    failed: int
    results: list[SymbolResult]


def write_json(path: Path, data: Any) -> None:
    """Backward-compatible wrapper around json_io.write_json."""
    from nse_nifty50_scraper.json_io import write_json as _write_json

    _write_json(path, data)


def latest_daily_record(data: Any) -> tuple[dict[str, Any], dt.date]:
    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, list):
        rows = [item for item in data if isinstance(item, dict)]
    else:
        raise ValueError("NSE response is not a JSON object or list of objects")

    dated_rows: list[tuple[dt.date, dict[str, Any]]] = []
    for row in rows:
        timestamp = row.get("mtimestamp")
        if isinstance(timestamp, str):
            dated_rows.append((parse_nse_timestamp(timestamp), row))

    if not dated_rows:
        raise ValueError("NSE response does not contain a row with mtimestamp")

    trade_date, record = max(dated_rows, key=lambda item: item[0])
    return record, trade_date


def run_fetch(
    symbols: list[SymbolConfig],
    from_date: dt.date,
    to_date: dt.date,
    output_dir: Path,
    runs_dir: Path,
    run_date: dt.date,
    mode: str = "daily",
    delay_seconds: float = 1.0,
    fail_threshold_percent: int = 80,
) -> RunResult:
    results: list[SymbolResult] = []

    with NSEClient() as client:
        for index, symbol in enumerate(symbols):
            if index > 0:
                time.sleep(delay_seconds)

            try:
                data = client.fetch_historical_data(symbol, from_date, to_date)

                if mode == "daily":
                    record, trade_date = latest_daily_record(data)
                    path = persist_daily_bar(output_dir, symbol.symbol, trade_date, record)
                    results.append(
                        SymbolResult(
                            symbol=symbol.symbol,
                            status="success",
                            path=str(path),
                            trade_date=format_nse_date(trade_date),
                        )
                    )
                elif mode == "window":
                    path = persist_window_response(output_dir, symbol.symbol, run_date, data)
                    results.append(
                        SymbolResult(symbol=symbol.symbol, status="success", path=str(path))
                    )
                else:
                    raise ValueError(f"Unsupported mode: {mode}")
            except (NSEClientError, ValueError) as exc:
                results.append(SymbolResult(symbol=symbol.symbol, status="failed", error=str(exc)))

    succeeded = sum(1 for item in results if item.status == "success")
    failed = len(results) - succeeded
    summary = RunResult(
        mode=mode,
        run_date=format_nse_date(run_date),
        from_date=format_nse_date(from_date),
        to_date=format_nse_date(to_date),
        attempted=len(results),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )

    persist_run_summary(
        run_summary_path(runs_dir, run_date),
        run_date,
        asdict(summary),
        kind="fetch",
    )

    if symbols and failed / len(symbols) * 100 >= fail_threshold_percent:
        raise RuntimeError(f"Too many symbols failed: {failed}/{len(symbols)}")

    return summary
