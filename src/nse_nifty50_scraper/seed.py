from __future__ import annotations

import datetime as dt
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import typer

from nse_nifty50_scraper.config import DEFAULT_CONFIG_PATH, filter_symbols, load_symbols
from nse_nifty50_scraper.dates import (
    format_nse_date,
    parse_nse_date,
    parse_nse_timestamp,
    today_ist,
)
from nse_nifty50_scraper.nse_client import NSEClient, NSEClientError
from nse_nifty50_scraper.paths import symbol_daily_response_path
from nse_nifty50_scraper.runner import write_json

app = typer.Typer(help="Seed historical NSE rows into daily JSON files.")


@dataclass
class ChunkResult:
    symbol: str
    from_date: str
    to_date: str
    rows_saved: int
    status: str
    error: str | None = None


@dataclass
class SeedResult:
    run_date: str
    from_date: str
    to_date: str
    chunk_days: int
    symbols: int
    chunks: list[ChunkResult]


def parse_symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip().upper() for part in value.split(",") if part.strip()]


def chunk_date_range(
    start_date: dt.date,
    end_date: dt.date,
    chunk_days: int,
) -> list[tuple[dt.date, dt.date]]:
    if chunk_days < 1:
        raise ValueError("chunk_days must be at least 1")
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    chunks: list[tuple[dt.date, dt.date]] = []
    current = start_date
    while current <= end_date:
        chunk_end = min(current + dt.timedelta(days=chunk_days - 1), end_date)
        chunks.append((current, chunk_end))
        current = chunk_end + dt.timedelta(days=1)
    return chunks


def response_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    raise ValueError("NSE response is not a JSON object or list of objects")


def save_rows(output_dir: Path, symbol: str, rows: list[dict[str, Any]]) -> int:
    saved = 0
    for row in rows:
        timestamp = row.get("mtimestamp")
        if not isinstance(timestamp, str):
            continue

        trade_date = parse_nse_timestamp(timestamp)
        path = symbol_daily_response_path(output_dir, symbol, trade_date)
        write_json(path, row)
        saved += 1

    return saved


def seed_history(
    symbols: str | None = None,
    years: int = 5,
    chunk_days: int = 90,
    from_date: str | None = None,
    to_date: str | None = None,
    config: Path = DEFAULT_CONFIG_PATH,
    output_dir: Path = Path("data/raw"),
    runs_dir: Path = Path("data/runs"),
    delay_seconds: float = 1.0,
) -> SeedResult:
    end = parse_nse_date(to_date) if to_date else today_ist()
    start = parse_nse_date(from_date) if from_date else end - dt.timedelta(days=years * 365)
    chunks = chunk_date_range(start, end, chunk_days)
    configured_symbols = load_symbols(config)
    selected_symbols = filter_symbols(configured_symbols, parse_symbols(symbols))
    chunk_results: list[ChunkResult] = []

    with NSEClient() as client:
        for symbol_index, symbol in enumerate(selected_symbols):
            for chunk_index, (chunk_start, chunk_end) in enumerate(chunks):
                if symbol_index > 0 or chunk_index > 0:
                    time.sleep(delay_seconds)

                try:
                    data = client.fetch_historical_data(symbol, chunk_start, chunk_end)
                    saved = save_rows(output_dir, symbol.symbol, response_rows(data))
                    chunk_results.append(
                        ChunkResult(
                            symbol=symbol.symbol,
                            from_date=format_nse_date(chunk_start),
                            to_date=format_nse_date(chunk_end),
                            rows_saved=saved,
                            status="success",
                        )
                    )
                except (NSEClientError, ValueError) as exc:
                    chunk_results.append(
                        ChunkResult(
                            symbol=symbol.symbol,
                            from_date=format_nse_date(chunk_start),
                            to_date=format_nse_date(chunk_end),
                            rows_saved=0,
                            status="failed",
                            error=str(exc),
                        )
                    )

    result = SeedResult(
        run_date=format_nse_date(today_ist()),
        from_date=format_nse_date(start),
        to_date=format_nse_date(end),
        chunk_days=chunk_days,
        symbols=len(selected_symbols),
        chunks=chunk_results,
    )
    write_json(runs_dir / f"seed-{result.run_date}.json", asdict(result))
    return result


@app.command()
def run(
    symbols: Annotated[
        str | None,
        typer.Option("--symbols", help="Comma-separated symbols. Defaults to all Nifty 50."),
    ] = None,
    years: Annotated[
        int, typer.Option("--years", help="Years to seed when dates are omitted.")
    ] = 5,
    chunk_days: Annotated[int, typer.Option("--chunk-days", help="Days per NSE API chunk.")] = 90,
    from_date: Annotated[
        str | None,
        typer.Option("--from-date", help="Start date in DD-MM-YYYY format."),
    ] = None,
    to_date: Annotated[
        str | None,
        typer.Option("--to-date", help="End date in DD-MM-YYYY format."),
    ] = None,
    config: Annotated[Path, typer.Option("--config")] = DEFAULT_CONFIG_PATH,
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("data/raw"),
    runs_dir: Annotated[Path, typer.Option("--runs-dir")] = Path("data/runs"),
    delay_seconds: Annotated[float, typer.Option("--delay-seconds")] = 1.0,
) -> None:
    result = seed_history(
        symbols=symbols,
        years=years,
        chunk_days=chunk_days,
        from_date=from_date,
        to_date=to_date,
        config=config,
        output_dir=output_dir,
        runs_dir=runs_dir,
        delay_seconds=delay_seconds,
    )
    succeeded = sum(1 for chunk in result.chunks if chunk.status == "success")
    failed = len(result.chunks) - succeeded
    rows_saved = sum(chunk.rows_saved for chunk in result.chunks)
    typer.echo(f"Seed complete: {rows_saved} rows saved, {succeeded} chunks ok, {failed} failed")


def main() -> None:
    app()
