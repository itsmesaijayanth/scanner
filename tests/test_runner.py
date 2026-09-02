from __future__ import annotations

import datetime as dt

from nse_nifty50_scraper.runner import latest_daily_record, write_json


def test_write_json_creates_parent_directory(tmp_path):
    path = tmp_path / "SBIN" / "2026" / "Aug" / "26" / "response.json"

    write_json(path, [{"symbol": "SBIN"}])

    assert path.exists()
    assert '"symbol": "SBIN"' in path.read_text(encoding="utf-8")


def test_latest_daily_record_uses_newest_mtimestamp():
    record, trade_date = latest_daily_record(
        [
            {"chSymbol": "SBIN", "mtimestamp": "25-Aug-2026", "chClosingPrice": 100},
            {"chSymbol": "SBIN", "mtimestamp": "26-Aug-2026", "chClosingPrice": 101},
        ]
    )

    assert trade_date == dt.date(2026, 8, 26)
    assert record["chClosingPrice"] == 101
