from __future__ import annotations

import datetime as dt

from nse_nifty50_scraper.dates import (
    date_path_parts,
    format_nse_date,
    parse_nse_date,
    parse_nse_timestamp,
    rolling_window,
)


def test_parse_and_format_nse_date():
    value = parse_nse_date("26-08-2026")

    assert value == dt.date(2026, 8, 26)
    assert format_nse_date(value) == "26-08-2026"


def test_rolling_window_uses_30_day_lookback():
    start, end = rolling_window(30, end_date=dt.date(2026, 8, 26))

    assert start == dt.date(2026, 7, 27)
    assert end == dt.date(2026, 8, 26)


def test_parse_nse_timestamp():
    assert parse_nse_timestamp("26-Aug-2026") == dt.date(2026, 8, 26)


def test_date_path_parts():
    assert date_path_parts(dt.date(2026, 8, 26)) == ("2026", "Aug", "26")
