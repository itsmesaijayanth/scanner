from __future__ import annotations

import datetime as dt

from nse_nifty50_scraper.paths import run_summary_path, safe_symbol_path, symbol_response_path


def test_safe_symbol_path_keeps_nse_symbols_readable():
    assert safe_symbol_path("M&M") == "MANDM"
    assert safe_symbol_path("BAJAJ-AUTO") == "BAJAJ-AUTO"


def test_symbol_response_path_uses_requested_layout(tmp_path):
    path = symbol_response_path(tmp_path, "SBIN", dt.date(2026, 8, 26))

    assert path == tmp_path / "SBIN" / "26-08-2026" / "response.json"


def test_run_summary_path(tmp_path):
    path = run_summary_path(tmp_path, dt.date(2026, 8, 26))

    assert path == tmp_path / "26-08-2026.json"
