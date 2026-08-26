from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from nse_nifty50_scraper.config import DEFAULT_CONFIG_PATH, filter_symbols, load_symbols
from nse_nifty50_scraper.dates import format_nse_date, parse_nse_date, rolling_window, today_ist
from nse_nifty50_scraper.runner import run_fetch

app = typer.Typer(help="Download NSE historical JSON data for Nifty 50 symbols.")


def parse_symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip().upper() for part in value.split(",") if part.strip()]


@app.command()
def fetch(
    symbols: Annotated[
        str | None,
        typer.Option("--symbols", help="Comma-separated symbols. Defaults to all Nifty 50."),
    ] = None,
    from_date: Annotated[
        str | None,
        typer.Option("--from-date", help="Start date in DD-MM-YYYY format."),
    ] = None,
    to_date: Annotated[
        str | None,
        typer.Option("--to-date", help="End date in DD-MM-YYYY format."),
    ] = None,
    days: Annotated[int, typer.Option("--days", help="Rolling window size.")] = 30,
    config: Annotated[
        Path,
        typer.Option("--config", help="Path to Nifty 50 symbol config."),
    ] = DEFAULT_CONFIG_PATH,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Base folder for per-symbol JSON data."),
    ] = Path("data/raw"),
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", help="Folder for run summary JSON files."),
    ] = Path("data/runs"),
    delay_seconds: Annotated[
        float,
        typer.Option("--delay-seconds", help="Delay between symbol requests."),
    ] = 1.0,
) -> None:
    if from_date or to_date:
        if not from_date or not to_date:
            raise typer.BadParameter("Use both --from-date and --to-date, or neither.")
        start = parse_nse_date(from_date)
        end = parse_nse_date(to_date)
    else:
        start, end = rolling_window(days)

    if start > end:
        raise typer.BadParameter("--from-date cannot be after --to-date.")

    configured_symbols = load_symbols(config)
    selected_symbols = filter_symbols(configured_symbols, parse_symbols(symbols))
    run_date = today_ist()

    typer.echo(
        f"Fetching {len(selected_symbols)} symbols for {format_nse_date(start)} "
        f"to {format_nse_date(end)}"
    )
    result = run_fetch(
        symbols=selected_symbols,
        from_date=start,
        to_date=end,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=run_date,
        delay_seconds=delay_seconds,
    )
    typer.echo(f"Done: {result.succeeded} succeeded, {result.failed} failed")


def main() -> None:
    app()
