from __future__ import annotations

import datetime as dt
from typing import Any

from nse_nifty50_scraper.dates import format_nse_date


def as_utc_midnight(value: dt.date) -> dt.datetime:
    return dt.datetime(value.year, value.month, value.day, tzinfo=dt.UTC)


def daily_bar_document(
    symbol: str,
    trade_date: dt.date,
    payload: dict[str, Any],
    *,
    source_path: str | None = None,
    updated_at: dt.datetime | None = None,
) -> dict[str, Any]:
    series = payload.get("chSeries")
    return {
        "symbol": symbol.upper(),
        "trade_date": as_utc_midnight(trade_date),
        "trade_date_nse": format_nse_date(trade_date),
        "series": series.upper() if isinstance(series, str) else series,
        "payload": payload,
        "source_path": source_path,
        "updated_at": updated_at or dt.datetime.now(tz=dt.UTC),
    }


def algo_result_document(
    algorithm: str,
    symbol: str,
    window_end_date: dt.date,
    payload: dict[str, Any],
    *,
    source_path: str | None = None,
    updated_at: dt.datetime | None = None,
) -> dict[str, Any]:
    return {
        "algorithm": algorithm,
        "symbol": symbol.upper(),
        "window_end_date": as_utc_midnight(window_end_date),
        "window_end_date_nse": format_nse_date(window_end_date),
        "payload": payload,
        "source_path": source_path,
        "updated_at": updated_at or dt.datetime.now(tz=dt.UTC),
    }


def run_summary_document(
    kind: str,
    run_date: dt.date,
    payload: dict[str, Any],
    *,
    source_path: str | None = None,
    updated_at: dt.datetime | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "run_date": as_utc_midnight(run_date),
        "run_date_nse": format_nse_date(run_date),
        "payload": payload,
        "source_path": source_path,
        "updated_at": updated_at or dt.datetime.now(tz=dt.UTC),
    }
