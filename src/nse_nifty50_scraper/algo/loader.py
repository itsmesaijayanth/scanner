from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from nse_nifty50_scraper.algo.models import DailyRow, DailyRowError
from nse_nifty50_scraper.paths import safe_symbol_path


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def iter_symbol_daily_files(raw_dir: Path, symbol: str) -> list[Path]:
    symbol_dir = raw_dir / safe_symbol_path(symbol)
    if not symbol_dir.exists():
        return []
    return sorted(symbol_dir.glob("[0-9][0-9][0-9][0-9]/*/*/response.json"))


def load_symbol_rows(raw_dir: Path, symbol: str) -> list[DailyRow]:
    rows_by_date = {}
    for path in iter_symbol_daily_files(raw_dir, symbol):
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        try:
            row = DailyRow.from_nse(data)
        except DailyRowError:
            continue
        rows_by_date[row.date] = row

    return [rows_by_date[date] for date in sorted(rows_by_date)]


def collect_trading_dates(raw_dir: Path, symbols: list[str]) -> list[dt.date]:
    dates: set[dt.date] = set()
    for symbol in symbols:
        for row in load_symbol_rows(raw_dir, symbol):
            dates.add(row.date)
    return sorted(dates)
