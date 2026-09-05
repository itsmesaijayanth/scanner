from __future__ import annotations

import datetime as dt
from pathlib import Path

import mongomock

from nse_nifty50_scraper.db.documents import daily_bar_document
from nse_nifty50_scraper.db.repositories import DailyBarRepository
from nse_nifty50_scraper.db.settings import MongoSettings
from nse_nifty50_scraper.db.store import MongoStore, reset_mongo_store
from nse_nifty50_scraper.json_io import write_json
from nse_nifty50_scraper.mongo_seed import (
    build_algo_document,
    build_daily_document,
    build_run_document,
    seed_daily_bars,
)


def test_daily_bar_repository_upserts_idempotently():
    collection = mongomock.MongoClient()["test"]["daily_bars"]
    repo = DailyBarRepository(collection)
    payload = {"chSymbol": "SBIN", "chSeries": "EQ", "mtimestamp": "04-Sep-2026"}

    repo.upsert("SBIN", dt.date(2026, 9, 4), payload, source_path="a.json")
    updated = {**payload, "chClosingPrice": 101}
    repo.upsert("SBIN", dt.date(2026, 9, 4), updated, source_path="a.json")

    docs = list(collection.find())
    assert len(docs) == 1
    assert docs[0]["payload"]["chClosingPrice"] == 101


def test_build_daily_and_algo_documents_from_disk(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    algo_dir = tmp_path / "algo"
    daily_path = raw_dir / "SBIN" / "2026" / "Sep" / "04" / "response.json"
    algo_path = (
        algo_dir / "swing_momentum" / "SBIN" / "2026" / "Sep" / "04" / "window" / "response.json"
    )
    write_json(
        daily_path,
        {
            "chSymbol": "SBIN",
            "chSeries": "EQ",
            "mtimestamp": "04-Sep-2026",
            "chClosingPrice": 100,
        },
    )
    write_json(
        algo_path,
        {
            "algorithm": "swing_momentum",
            "symbol": "SBIN",
            "window": {"end_date": "04-09-2026"},
        },
    )

    daily = build_daily_document(daily_path, raw_dir)
    algo = build_algo_document(algo_path, algo_dir)

    assert daily is not None
    assert daily["symbol"] == "SBIN"
    assert algo is not None
    assert algo["window_end_date_nse"] == "04-09-2026"


def test_build_run_document_infers_kind(tmp_path: Path):
    path = tmp_path / "seed-04-09-2026.json"
    write_json(path, {"run_date": "04-09-2026", "symbols": 1})

    document = build_run_document(path)

    assert document is not None
    assert document["kind"] == "seed"
    assert document["run_date_nse"] == "04-09-2026"


def test_seed_daily_bars_bulk_imports(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    path = raw_dir / "TCS" / "2026" / "Sep" / "04" / "response.json"
    write_json(
        path,
        {
            "chSymbol": "TCS",
            "chSeries": "EQ",
            "mtimestamp": "04-Sep-2026",
            "chClosingPrice": 3000,
        },
    )
    collection = mongomock.MongoClient()["test"]["daily_bars"]
    repo = DailyBarRepository(collection)

    stats = seed_daily_bars(repo, raw_dir, symbols={"TCS"}, batch_size=10)

    assert stats.scanned == 1
    assert stats.imported == 1
    assert collection.count_documents({}) == 1
    assert collection.find_one({"symbol": "TCS"})["payload"]["chClosingPrice"] == 3000


def test_mongo_store_with_mongomock():
    reset_mongo_store()
    client = mongomock.MongoClient()
    settings = MongoSettings(enabled=True, database="scanner_test")
    connection = type(
        "Conn",
        (),
        {
            "settings": settings,
            "db": client[settings.database],
            "close": lambda self=None: None,
        },
    )()
    store = MongoStore(connection, settings=settings)  # type: ignore[arg-type]
    store._indexes_ready = True

    payload = daily_bar_document(
        "INFY",
        dt.date(2026, 9, 4),
        {"chSymbol": "INFY", "chSeries": "EQ", "mtimestamp": "04-Sep-2026"},
    )
    store.daily_bars.bulk_upsert([payload])

    assert store.daily_bars.collection.count_documents({"symbol": "INFY"}) == 1
    reset_mongo_store()
