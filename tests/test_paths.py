from __future__ import annotations

import datetime as dt

from nse_nifty50_scraper.paths import (
    run_summary_path,
    safe_symbol_path,
    symbol_daily_response_path,
    symbol_window_response_path,
)


def test_safe_symbol_path_keeps_nse_symbols_readable():
    assert safe_symbol_path("M&M") == "MANDM"
    assert safe_symbol_path("BAJAJ-AUTO") == "BAJAJ-AUTO"


def test_symbol_daily_response_path_uses_requested_layout(tmp_path):
    path = symbol_daily_response_path(tmp_path, "SBIN", dt.date(2026, 8, 26))

    assert path == tmp_path / "SBIN" / "2026" / "Aug" / "26" / "response.json"


def test_symbol_window_response_path_keeps_window_mode_available(tmp_path):
    path = symbol_window_response_path(tmp_path, "SBIN", dt.date(2026, 8, 26))

    assert path == tmp_path / "SBIN" / "windows" / "26-08-2026" / "response.json"


def test_run_summary_path(tmp_path):
    path = run_summary_path(tmp_path, dt.date(2026, 8, 26))

    assert path == tmp_path / "26-08-2026.json"
