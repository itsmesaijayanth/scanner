from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from nse_nifty50_scraper.algo.loader import collect_trading_dates, load_symbol_rows
from nse_nifty50_scraper.algo.models import DailyRow
from nse_nifty50_scraper.algo.swing_momentum import ALGORITHM_NAME, analyze_swing_momentum
from nse_nifty50_scraper.config import SymbolConfig
from nse_nifty50_scraper.dates import format_nse_date
from nse_nifty50_scraper.paths import algorithm_window_response_path
from nse_nifty50_scraper.runner import write_json


@dataclass
class AlgoSymbolResult:
    symbol: str
    status: str
    path: str | None = None
    window_end_date: str | None = None
    error: str | None = None


@dataclass
class AlgoRunResult:
    algorithm: str
    run_date: str
    requested_end_date: str | None
    window_days: int
    attempted: int
    succeeded: int
    failed: int
    skipped: int
    results: list[AlgoSymbolResult]


@dataclass
class BackfillResult:
    algorithm: str
    run_date: str
    window_days: int
    from_date: str | None
    to_date: str | None
    dates_total: int
    dates_processed: int
    dates_skipped: int
    succeeded: int
    failed: int
    skipped: int


def _run_symbol(
    symbol: SymbolConfig,
    rows: list[DailyRow],
    output_dir: Path,
    end_date: dt.date | None,
    window_days: int,
    tolerance: float,
    skip_existing: bool,
) -> AlgoSymbolResult:
    try:
        analysis = analyze_swing_momentum(
            symbol=symbol.symbol,
            rows=rows,
            end_date=end_date,
            window_days=window_days,
            tolerance=tolerance,
        )
        output_end = analysis["window"]["end_date"]
        if output_end is None:
            raise ValueError("No available trading date for output path")

        output_end_date = dt.datetime.strptime(output_end, "%d-%m-%Y").date()
        path = algorithm_window_response_path(
            output_dir,
            ALGORITHM_NAME,
            symbol.symbol,
            output_end_date,
        )
        if skip_existing and path.exists():
            return AlgoSymbolResult(
                symbol=symbol.symbol,
                status="skipped",
                path=str(path),
                window_end_date=output_end,
            )

        write_json(path, analysis)
        return AlgoSymbolResult(
            symbol=symbol.symbol,
            status="success",
            path=str(path),
            window_end_date=output_end,
        )
    except ValueError as exc:
        return AlgoSymbolResult(symbol=symbol.symbol, status="failed", error=str(exc))


def run_swing_momentum(
    symbols: list[SymbolConfig],
    raw_dir: Path,
    output_dir: Path,
    runs_dir: Path,
    run_date: dt.date,
    end_date: dt.date | None = None,
    window_days: int = 30,
    tolerance: float = 0.01,
    rows_by_symbol: dict[str, list[DailyRow]] | None = None,
    skip_existing: bool = False,
    write_summary: bool = True,
) -> AlgoRunResult:
    results: list[AlgoSymbolResult] = []

    for symbol in symbols:
        rows = (
            rows_by_symbol[symbol.symbol]
            if rows_by_symbol is not None
            else load_symbol_rows(raw_dir, symbol.symbol)
        )
        results.append(
            _run_symbol(
                symbol=symbol,
                rows=rows,
                output_dir=output_dir,
                end_date=end_date,
                window_days=window_days,
                tolerance=tolerance,
                skip_existing=skip_existing,
            )
        )

    succeeded = sum(1 for item in results if item.status == "success")
    failed = sum(1 for item in results if item.status == "failed")
    skipped = sum(1 for item in results if item.status == "skipped")
    summary = AlgoRunResult(
        algorithm=ALGORITHM_NAME,
        run_date=format_nse_date(run_date),
        requested_end_date=format_nse_date(end_date) if end_date else None,
        window_days=window_days,
        attempted=len(results),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
    )
    if write_summary:
        write_json(runs_dir / f"{ALGORITHM_NAME}-{format_nse_date(run_date)}.json", asdict(summary))
    return summary


def backfill_swing_momentum(
    symbols: list[SymbolConfig],
    raw_dir: Path,
    output_dir: Path,
    runs_dir: Path,
    run_date: dt.date,
    window_days: int = 30,
    tolerance: float = 0.01,
    from_date: dt.date | None = None,
    to_date: dt.date | None = None,
    skip_existing: bool = True,
    on_date_complete: Callable[[int, int, dt.date, AlgoRunResult], None] | None = None,
) -> BackfillResult:
    symbol_names = [symbol.symbol for symbol in symbols]
    rows_by_symbol = {symbol.symbol: load_symbol_rows(raw_dir, symbol.symbol) for symbol in symbols}
    trading_dates = collect_trading_dates(raw_dir, symbol_names)
    if from_date is not None:
        trading_dates = [date for date in trading_dates if date >= from_date]
    if to_date is not None:
        trading_dates = [date for date in trading_dates if date <= to_date]

    dates_processed = 0
    dates_skipped = 0
    total_succeeded = 0
    total_failed = 0
    total_skipped = 0

    for index, end_date in enumerate(trading_dates, start=1):
        result = run_swing_momentum(
            symbols=symbols,
            raw_dir=raw_dir,
            output_dir=output_dir,
            runs_dir=runs_dir,
            run_date=run_date,
            end_date=end_date,
            window_days=window_days,
            tolerance=tolerance,
            rows_by_symbol=rows_by_symbol,
            skip_existing=skip_existing,
            write_summary=False,
        )
        if result.skipped == result.attempted and result.attempted > 0:
            dates_skipped += 1
        else:
            dates_processed += 1

        total_succeeded += result.succeeded
        total_failed += result.failed
        total_skipped += result.skipped

        if on_date_complete is not None:
            on_date_complete(index, len(trading_dates), end_date, result)

    summary = BackfillResult(
        algorithm=ALGORITHM_NAME,
        run_date=format_nse_date(run_date),
        window_days=window_days,
        from_date=format_nse_date(from_date) if from_date else None,
        to_date=format_nse_date(to_date) if to_date else None,
        dates_total=len(trading_dates),
        dates_processed=dates_processed,
        dates_skipped=dates_skipped,
        succeeded=total_succeeded,
        failed=total_failed,
        skipped=total_skipped,
    )
    write_json(
        runs_dir / f"{ALGORITHM_NAME}-backfill-{format_nse_date(run_date)}.json",
        asdict(summary),
    )
    return summary
