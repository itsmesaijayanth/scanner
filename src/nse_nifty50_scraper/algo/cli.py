from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import typer

from nse_nifty50_scraper.algo.runner import (
    AlgoRunResult,
    backfill_swing_momentum,
    run_swing_momentum,
)
from nse_nifty50_scraper.config import DEFAULT_CONFIG_PATH, filter_symbols, load_symbols
from nse_nifty50_scraper.dates import format_nse_date, parse_nse_date, today_ist
from nse_nifty50_scraper.seed import parse_symbols

app = typer.Typer(help="Run swing momentum analysis from stored NSE daily data.")


@app.command()
def run(
    symbols: Annotated[
        str | None,
        typer.Option("--symbols", help="Comma-separated symbols. Defaults to all Nifty 50."),
    ] = None,
    end_date: Annotated[
        str | None,
        typer.Option("--end-date", help="Window end date in DD-MM-YYYY format."),
    ] = None,
    window_days: Annotated[
        int, typer.Option("--window-days", help="Calendar-day window size.")
    ] = 30,
    backfill: Annotated[
        bool,
        typer.Option(
            "--backfill",
            help="Run the algorithm for every trading date found in seeded raw data.",
        ),
    ] = False,
    from_date: Annotated[
        str | None,
        typer.Option("--from-date", help="Backfill start date in DD-MM-YYYY format."),
    ] = None,
    to_date: Annotated[
        str | None,
        typer.Option("--to-date", help="Backfill end date in DD-MM-YYYY format."),
    ] = None,
    no_resume: Annotated[
        bool,
        typer.Option(
            "--no-resume",
            help="Recompute outputs even when the target analysis file already exists.",
        ),
    ] = False,
    raw_dir: Annotated[Path, typer.Option("--raw-dir")] = Path("data/raw"),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("data/algo"),
    runs_dir: Annotated[Path, typer.Option("--runs-dir")] = Path("data/runs"),
    config: Annotated[Path, typer.Option("--config")] = DEFAULT_CONFIG_PATH,
    tolerance: Annotated[float, typer.Option("--tolerance")] = 0.01,
) -> None:
    if backfill and end_date is not None:
        raise typer.BadParameter(
            "--end-date cannot be used with --backfill; use --to-date instead."
        )

    configured_symbols = load_symbols(config)
    selected_symbols = filter_symbols(configured_symbols, parse_symbols(symbols))
    parsed_from_date = parse_nse_date(from_date) if from_date else None
    parsed_to_date = parse_nse_date(to_date) if to_date else None

    if backfill:

        def on_progress(index: int, total: int, date: dt.date, result: AlgoRunResult) -> None:
            typer.echo(
                f"[{index}/{total}] {format_nse_date(date)}: "
                f"{result.succeeded} succeeded, {result.failed} failed, {result.skipped} skipped"
            )

        result = backfill_swing_momentum(
            symbols=selected_symbols,
            raw_dir=raw_dir,
            output_dir=output_dir,
            runs_dir=runs_dir,
            run_date=today_ist(),
            window_days=window_days,
            tolerance=tolerance,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            skip_existing=not no_resume,
            on_date_complete=on_progress,
        )
        typer.echo(
            "Backfill complete: "
            f"{result.dates_processed} dates processed, "
            f"{result.dates_skipped} dates skipped, "
            f"{result.succeeded} succeeded, "
            f"{result.failed} failed, "
            f"{result.skipped} symbol outputs skipped"
        )
        return

    result = run_swing_momentum(
        symbols=selected_symbols,
        raw_dir=raw_dir,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=today_ist(),
        end_date=parse_nse_date(end_date) if end_date else None,
        window_days=window_days,
        tolerance=tolerance,
        skip_existing=not no_resume,
    )
    typer.echo(
        f"Done: {result.succeeded} succeeded, {result.failed} failed, {result.skipped} skipped"
    )


def main() -> None:
    app()
