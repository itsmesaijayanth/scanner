from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from nse_nifty50_scraper.dates import format_nse_date


def safe_symbol_path(symbol: str) -> str:
    cleaned = symbol.upper().strip()
    cleaned = cleaned.replace("&", "AND")
    cleaned = re.sub(r"[^A-Z0-9._-]+", "-", cleaned)
    return cleaned.strip("-")


def symbol_response_path(output_dir: Path, symbol: str, run_date: dt.date) -> Path:
    return output_dir / safe_symbol_path(symbol) / format_nse_date(run_date) / "response.json"


def run_summary_path(runs_dir: Path, run_date: dt.date) -> Path:
    return runs_dir / f"{format_nse_date(run_date)}.json"
