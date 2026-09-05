from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import typer

from nse_nifty50_scraper.algo.swing_momentum import ALGORITHM_NAME
from nse_nifty50_scraper.dates import parse_nse_date, parse_nse_timestamp, today_ist
from nse_nifty50_scraper.db.connection import MongoConnection
from nse_nifty50_scraper.db.documents import (
    algo_result_document,
    daily_bar_document,
    run_summary_document,
)
from nse_nifty50_scraper.db.repositories import (
    AlgoResultRepository,
    DailyBarRepository,
    RunSummaryRepository,
)
from nse_nifty50_scraper.db.settings import MongoSettings, load_mongo_settings
from nse_nifty50_scraper.db.store import MongoStore
from nse_nifty50_scraper.paths import safe_symbol_path

app = typer.Typer(help="Seed existing JSON data into MongoDB.")

DAILY_PATH_RE = re.compile(
    r"(?P<symbol>[^/\\]+)[/\\](?P<year>\d{4})[/\\](?P<month>[A-Za-z]{3})"
    r"[/\\](?P<day>\d{2})[/\\]response\.json$"
)
ALGO_PATH_RE = re.compile(
    r"(?P<algorithm>[^/\\]+)[/\\](?P<symbol>[^/\\]+)[/\\](?P<year>\d{4})[/\\]"
    r"(?P<month>[A-Za-z]{3})[/\\](?P<day>\d{2})[/\\]window[/\\]response\.json$"
)
MONTH_TO_NUM = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


@dataclass
class SeedStats:
    kind: str
    scanned: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class MongoSeedResult:
    run_date: str
    raw_dir: str
    algo_dir: str
    runs_dir: str
    batch_size: int
    stats: list[SeedStats]


def parse_symbols(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {part.strip().upper() for part in value.split(",") if part.strip()}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def path_date_from_parts(year: str, month: str, day: str) -> dt.date | None:
    month_num = MONTH_TO_NUM.get(month)
    if month_num is None:
        return None
    try:
        return dt.date(int(year), month_num, int(day))
    except ValueError:
        return None


def iter_daily_files(raw_dir: Path, symbols: set[str] | None) -> Iterator[Path]:
    if symbols:
        for symbol in sorted(symbols):
            symbol_dir = raw_dir / safe_symbol_path(symbol)
            if symbol_dir.exists():
                yield from sorted(symbol_dir.glob("[0-9][0-9][0-9][0-9]/*/*/response.json"))
        return

    yield from sorted(raw_dir.glob("*/[0-9][0-9][0-9][0-9]/*/*/response.json"))


def iter_algo_files(
    algo_dir: Path,
    algorithm: str,
    symbols: set[str] | None,
) -> Iterator[Path]:
    base = algo_dir / algorithm
    if not base.exists():
        return

    if symbols:
        for symbol in sorted(symbols):
            symbol_dir = base / safe_symbol_path(symbol)
            if symbol_dir.exists():
                yield from sorted(symbol_dir.glob("[0-9][0-9][0-9][0-9]/*/*/window/response.json"))
        return

    yield from sorted(base.glob("*/[0-9][0-9][0-9][0-9]/*/*/window/response.json"))


def build_daily_document(path: Path, raw_dir: Path) -> dict[str, Any] | None:
    relative = path.relative_to(raw_dir).as_posix()
    match = DAILY_PATH_RE.search(relative)
    if match is None:
        return None

    payload = load_json(path)
    if not isinstance(payload, dict):
        return None

    symbol = str(payload.get("chSymbol") or match.group("symbol")).upper()
    timestamp = payload.get("mtimestamp")
    if isinstance(timestamp, str):
        trade_date = parse_nse_timestamp(timestamp)
    else:
        trade_date = path_date_from_parts(
            match.group("year"),
            match.group("month"),
            match.group("day"),
        )
        if trade_date is None:
            return None

    return daily_bar_document(symbol, trade_date, payload, source_path=str(path))


def build_algo_document(path: Path, algo_dir: Path) -> dict[str, Any] | None:
    relative = path.relative_to(algo_dir).as_posix()
    match = ALGO_PATH_RE.search(relative)
    if match is None:
        return None

    payload = load_json(path)
    if not isinstance(payload, dict):
        return None

    algorithm = str(payload.get("algorithm") or match.group("algorithm"))
    symbol = str(payload.get("symbol") or match.group("symbol")).upper()
    window = payload.get("window")
    end_date_raw = window.get("end_date") if isinstance(window, dict) else None
    if isinstance(end_date_raw, str):
        window_end_date = parse_nse_date(end_date_raw)
    else:
        window_end_date = path_date_from_parts(
            match.group("year"),
            match.group("month"),
            match.group("day"),
        )
        if window_end_date is None:
            return None

    return algo_result_document(
        algorithm,
        symbol,
        window_end_date,
        payload,
        source_path=str(path),
    )


def infer_run_kind(path: Path) -> str:
    name = path.stem
    if name.startswith("seed-"):
        return "seed"
    if name.startswith(f"{ALGORITHM_NAME}-backfill-"):
        return f"{ALGORITHM_NAME}_backfill"
    if name.startswith(f"{ALGORITHM_NAME}-"):
        return ALGORITHM_NAME
    return "fetch"


def infer_run_date(path: Path, payload: dict[str, Any]) -> dt.date | None:
    for key in ("run_date",):
        value = payload.get(key)
        if isinstance(value, str):
            try:
                return parse_nse_date(value)
            except ValueError:
                pass

    stem = path.stem
    for prefix in (f"{ALGORITHM_NAME}-backfill-", f"{ALGORITHM_NAME}-", "seed-", ""):
        if stem.startswith(prefix):
            candidate = stem.removeprefix(prefix)
            try:
                return parse_nse_date(candidate)
            except ValueError:
                continue
    return None


def build_run_document(path: Path) -> dict[str, Any] | None:
    payload = load_json(path)
    if not isinstance(payload, dict):
        return None

    run_date = infer_run_date(path, payload)
    if run_date is None:
        return None

    return run_summary_document(
        infer_run_kind(path),
        run_date,
        payload,
        source_path=str(path),
    )


def seed_daily_bars(
    repo: DailyBarRepository,
    raw_dir: Path,
    symbols: set[str] | None,
    batch_size: int,
) -> SeedStats:
    stats = SeedStats(kind="daily_bars")
    batch: list[dict[str, Any]] = []

    for path in iter_daily_files(raw_dir, symbols):
        stats.scanned += 1
        try:
            document = build_daily_document(path, raw_dir)
            if document is None:
                stats.skipped += 1
                continue
            batch.append(document)
            if len(batch) >= batch_size:
                repo.bulk_upsert(batch)
                stats.imported += len(batch)
                batch.clear()
        except Exception:
            stats.failed += 1

    if batch:
        repo.bulk_upsert(batch)
        stats.imported += len(batch)
    return stats


def seed_algo_results(
    repo: AlgoResultRepository,
    algo_dir: Path,
    algorithm: str,
    symbols: set[str] | None,
    batch_size: int,
) -> SeedStats:
    stats = SeedStats(kind="algo_results")
    batch: list[dict[str, Any]] = []

    for path in iter_algo_files(algo_dir, algorithm, symbols):
        stats.scanned += 1
        try:
            document = build_algo_document(path, algo_dir)
            if document is None:
                stats.skipped += 1
                continue
            batch.append(document)
            if len(batch) >= batch_size:
                repo.bulk_upsert(batch)
                stats.imported += len(batch)
                batch.clear()
        except Exception:
            stats.failed += 1

    if batch:
        repo.bulk_upsert(batch)
        stats.imported += len(batch)
    return stats


def seed_run_summaries(
    repo: RunSummaryRepository,
    runs_dir: Path,
    batch_size: int,
) -> SeedStats:
    stats = SeedStats(kind="runs")
    if not runs_dir.exists():
        return stats

    batch: list[dict[str, Any]] = []
    for path in sorted(runs_dir.glob("*.json")):
        stats.scanned += 1
        try:
            document = build_run_document(path)
            if document is None:
                stats.skipped += 1
                continue
            batch.append(document)
            if len(batch) >= batch_size:
                repo.bulk_upsert(batch)
                stats.imported += len(batch)
                batch.clear()
        except Exception:
            stats.failed += 1

    if batch:
        repo.bulk_upsert(batch)
        stats.imported += len(batch)
    return stats


def create_enabled_store(settings: MongoSettings | None = None) -> MongoStore:
    resolved = settings or load_mongo_settings()
    if not resolved.enabled:
        # Allow explicit CLI seed runs with default localhost URI.
        resolved = resolved.model_copy(update={"enabled": True})
    connection = MongoConnection(resolved)
    connection.ping()
    store = MongoStore(connection, settings=resolved)
    store.ensure_ready()
    return store


def seed_mongo_from_json(
    raw_dir: Path = Path("data/raw"),
    algo_dir: Path = Path("data/algo"),
    runs_dir: Path = Path("data/runs"),
    algorithm: str = ALGORITHM_NAME,
    symbols: str | None = None,
    only: str = "all",
    batch_size: int = 500,
    settings: MongoSettings | None = None,
) -> MongoSeedResult:
    if only not in {"all", "raw", "algo", "runs"}:
        raise ValueError("--only must be one of: all, raw, algo, runs")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    selected_symbols = parse_symbols(symbols)
    store = create_enabled_store(settings)
    stats: list[SeedStats] = []

    try:
        if only in {"all", "raw"}:
            stats.append(seed_daily_bars(store.daily_bars, raw_dir, selected_symbols, batch_size))
        if only in {"all", "algo"}:
            stats.append(
                seed_algo_results(
                    store.algo_results,
                    algo_dir,
                    algorithm,
                    selected_symbols,
                    batch_size,
                )
            )
        if only in {"all", "runs"}:
            stats.append(seed_run_summaries(store.runs, runs_dir, batch_size))
    finally:
        store.connection.close()

    return MongoSeedResult(
        run_date=today_ist().strftime("%d-%m-%Y"),
        raw_dir=str(raw_dir),
        algo_dir=str(algo_dir),
        runs_dir=str(runs_dir),
        batch_size=batch_size,
        stats=stats,
    )


@app.command("run")
def run(
    raw_dir: Annotated[Path, typer.Option("--raw-dir")] = Path("data/raw"),
    algo_dir: Annotated[Path, typer.Option("--algo-dir")] = Path("data/algo"),
    runs_dir: Annotated[Path, typer.Option("--runs-dir")] = Path("data/runs"),
    algorithm: Annotated[str, typer.Option("--algorithm")] = ALGORITHM_NAME,
    symbols: Annotated[
        str | None,
        typer.Option("--symbols", help="Comma-separated symbols. Defaults to all found."),
    ] = None,
    only: Annotated[
        str,
        typer.Option("--only", help="Seed subset: all | raw | algo | runs"),
    ] = "all",
    batch_size: Annotated[int, typer.Option("--batch-size")] = 500,
) -> None:
    """Import existing on-disk JSON into MongoDB collections."""
    result = seed_mongo_from_json(
        raw_dir=raw_dir,
        algo_dir=algo_dir,
        runs_dir=runs_dir,
        algorithm=algorithm,
        symbols=symbols,
        only=only,
        batch_size=batch_size,
    )
    for item in result.stats:
        typer.echo(
            f"{item.kind}: scanned={item.scanned} imported={item.imported} "
            f"skipped={item.skipped} failed={item.failed}"
        )
    typer.echo(f"Mongo seed complete ({asdict(result)['run_date']})")


def main() -> None:
    app()
