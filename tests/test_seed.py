from __future__ import annotations

import datetime as dt

from nse_nifty50_scraper.seed import chunk_date_range, response_rows


def test_chunk_date_range_splits_inclusive_chunks():
    chunks = chunk_date_range(dt.date(2026, 1, 1), dt.date(2026, 1, 10), 4)

    assert chunks == [
        (dt.date(2026, 1, 1), dt.date(2026, 1, 4)),
        (dt.date(2026, 1, 5), dt.date(2026, 1, 8)),
        (dt.date(2026, 1, 9), dt.date(2026, 1, 10)),
    ]


def test_response_rows_accepts_object_or_list():
    row = {"chSymbol": "SBIN"}

    assert response_rows(row) == [row]
    assert response_rows([row, "ignore"]) == [row]
