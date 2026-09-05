from __future__ import annotations

import datetime as dt

from nse_nifty50_scraper.db.documents import (
    algo_result_document,
    as_utc_midnight,
    daily_bar_document,
    run_summary_document,
)


def test_daily_bar_document_shape():
    payload = {
        "chSymbol": "SBIN",
        "chSeries": "EQ",
        "mtimestamp": "04-Sep-2026",
        "chClosingPrice": 100,
    }

    document = daily_bar_document(
        "sbin",
        dt.date(2026, 9, 4),
        payload,
        source_path="data/raw/SBIN/2026/Sep/04/response.json",
    )

    assert document["symbol"] == "SBIN"
    assert document["series"] == "EQ"
    assert document["trade_date"] == as_utc_midnight(dt.date(2026, 9, 4))
    assert document["trade_date_nse"] == "04-09-2026"
    assert document["payload"] == payload
    assert document["source_path"].endswith("response.json")


def test_algo_and_run_documents():
    algo = algo_result_document(
        "swing_momentum",
        "TCS",
        dt.date(2026, 9, 4),
        {"algorithm": "swing_momentum"},
    )
    run = run_summary_document("fetch", dt.date(2026, 9, 4), {"attempted": 1})

    assert algo["algorithm"] == "swing_momentum"
    assert algo["window_end_date_nse"] == "04-09-2026"
    assert run["kind"] == "fetch"
    assert run["run_date_nse"] == "04-09-2026"
