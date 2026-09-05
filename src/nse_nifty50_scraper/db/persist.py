from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from nse_nifty50_scraper.db.store import mongo_write
from nse_nifty50_scraper.json_io import write_json
from nse_nifty50_scraper.paths import (
    algorithm_window_response_path,
    symbol_daily_response_path,
    symbol_window_response_path,
)


def persist_daily_bar(
    output_dir: Path,
    symbol: str,
    trade_date: dt.date,
    payload: dict[str, Any],
) -> Path:
    path = symbol_daily_response_path(output_dir, symbol, trade_date)
    write_json(path, payload)
    mongo_write(
        "daily_bar upsert",
        lambda store: store.upsert_daily_bar(
            symbol,
            trade_date,
            payload,
            source_path=str(path),
        ),
    )
    return path


def persist_window_response(
    output_dir: Path,
    symbol: str,
    run_date: dt.date,
    payload: Any,
) -> Path:
    path = symbol_window_response_path(output_dir, symbol, run_date)
    write_json(path, payload)
    return path


def persist_algo_result(
    output_dir: Path,
    algorithm: str,
    symbol: str,
    window_end_date: dt.date,
    payload: dict[str, Any],
) -> Path:
    path = algorithm_window_response_path(output_dir, algorithm, symbol, window_end_date)
    write_json(path, payload)
    mongo_write(
        "algo_result upsert",
        lambda store: store.upsert_algo_result(
            algorithm,
            symbol,
            window_end_date,
            payload,
            source_path=str(path),
        ),
    )
    return path


def persist_run_summary(
    path: Path,
    run_date: dt.date,
    payload: dict[str, Any],
    *,
    kind: str,
) -> Path:
    write_json(path, payload)
    mongo_write(
        "run_summary upsert",
        lambda store: store.upsert_run_summary(
            kind,
            run_date,
            payload,
            source_path=str(path),
        ),
    )
    return path
