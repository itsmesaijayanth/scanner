from __future__ import annotations

from nse_nifty50_scraper.algo.loader import load_symbol_rows
from nse_nifty50_scraper.runner import write_json


def test_load_symbol_rows_reads_daily_layout_and_sorts_by_mtimestamp(tmp_path):
    write_json(
        tmp_path / "SBIN" / "2026" / "Sep" / "02" / "response.json",
        {
            "chSymbol": "SBIN",
            "mtimestamp": "02-Sep-2026",
            "chOpeningPrice": 102,
            "chTradeHighPrice": 105,
            "chTradeLowPrice": 101,
            "chClosingPrice": 104,
        },
    )
    write_json(
        tmp_path / "SBIN" / "2026" / "Sep" / "01" / "response.json",
        {
            "chSymbol": "SBIN",
            "mtimestamp": "01-Sep-2026",
            "chOpeningPrice": 100,
            "chTradeHighPrice": 103,
            "chTradeLowPrice": 99,
            "chClosingPrice": 102,
        },
    )

    rows = load_symbol_rows(tmp_path, "SBIN")

    assert [row.close for row in rows] == [102, 104]
