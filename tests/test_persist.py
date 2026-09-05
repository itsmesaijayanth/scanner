from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

from nse_nifty50_scraper.db.persist import persist_daily_bar
from nse_nifty50_scraper.db.store import reset_mongo_store


def teardown_function() -> None:
    reset_mongo_store()


def test_persist_daily_bar_writes_json_and_mongo(tmp_path, monkeypatch):
    monkeypatch.setenv("MONGO_ENABLED", "true")
    reset_mongo_store()

    store = MagicMock()
    with patch("nse_nifty50_scraper.db.store.get_mongo_store", return_value=store):
        path = persist_daily_bar(
            tmp_path,
            "SBIN",
            dt.date(2026, 9, 4),
            {
                "chSymbol": "SBIN",
                "chSeries": "EQ",
                "mtimestamp": "04-Sep-2026",
                "chClosingPrice": 100,
            },
        )

    assert path.exists()
    store.upsert_daily_bar.assert_called_once()
    args = store.upsert_daily_bar.call_args
    assert args.args[0] == "SBIN"
    assert args.args[1] == dt.date(2026, 9, 4)


def test_persist_daily_bar_skips_mongo_when_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.delenv("MONGO_ENABLED", raising=False)
    reset_mongo_store()

    with patch("nse_nifty50_scraper.db.store.get_mongo_store", return_value=None) as get_store:
        path = persist_daily_bar(
            tmp_path,
            "SBIN",
            dt.date(2026, 9, 4),
            {"chSymbol": "SBIN", "mtimestamp": "04-Sep-2026"},
        )

    assert path.exists()
    get_store.assert_called()
