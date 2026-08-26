from __future__ import annotations

import datetime as dt
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nse_nifty50_scraper.config import SymbolConfig
from nse_nifty50_scraper.dates import format_nse_date
from nse_nifty50_scraper.nse_client import NSEClient, NSEClientError
from nse_nifty50_scraper.paths import run_summary_path, symbol_response_path


@dataclass
class SymbolResult:
    symbol: str
    status: str
    path: str | None = None
    error: str | None = None


@dataclass
class RunResult:
    run_date: str
    from_date: str
    to_date: str
    attempted: int
    succeeded: int
    failed: int
    results: list[SymbolResult]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_fetch(
    symbols: list[SymbolConfig],
    from_date: dt.date,
    to_date: dt.date,
    output_dir: Path,
    runs_dir: Path,
    run_date: dt.date,
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
                path = symbol_response_path(output_dir, symbol.symbol, run_date)
                write_json(path, data)
                results.append(SymbolResult(symbol=symbol.symbol, status="success", path=str(path)))
            except NSEClientError as exc:
                results.append(SymbolResult(symbol=symbol.symbol, status="failed", error=str(exc)))

    succeeded = sum(1 for item in results if item.status == "success")
    failed = len(results) - succeeded
    summary = RunResult(
        run_date=format_nse_date(run_date),
        from_date=format_nse_date(from_date),
        to_date=format_nse_date(to_date),
        attempted=len(results),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )

    write_json(run_summary_path(runs_dir, run_date), asdict(summary))

    if symbols and failed / len(symbols) * 100 >= fail_threshold_percent:
        raise RuntimeError(f"Too many symbols failed: {failed}/{len(symbols)}")

    return summary
