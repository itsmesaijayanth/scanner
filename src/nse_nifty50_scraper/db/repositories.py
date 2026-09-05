from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from pymongo import ReplaceOne
from pymongo.collection import Collection
from pymongo.results import BulkWriteResult

from nse_nifty50_scraper.db.documents import (
    algo_result_document,
    daily_bar_document,
    run_summary_document,
)


def _bulk_replace(
    collection: Collection,
    documents: Sequence[dict[str, Any]],
    filter_for: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    ordered: bool = False,
) -> int:
    if not documents:
        return 0

    operations = [ReplaceOne(filter_for(doc), doc, upsert=True) for doc in documents]
    try:
        result: BulkWriteResult = collection.bulk_write(operations, ordered=ordered)
        return result.upserted_count + result.modified_count + result.matched_count
    except TypeError:
        # mongomock (and some stubs) lack full pymongo bulk ReplaceOne parity.
        for doc in documents:
            collection.replace_one(filter_for(doc), doc, upsert=True)
        return len(documents)


class DailyBarRepository:
    def __init__(self, collection: Collection) -> None:
        self.collection = collection

    def upsert(
        self,
        symbol: str,
        trade_date: dt.date,
        payload: dict[str, Any],
        *,
        source_path: str | None = None,
    ) -> None:
        document = daily_bar_document(symbol, trade_date, payload, source_path=source_path)
        self.collection.replace_one(
            {"symbol": document["symbol"], "trade_date": document["trade_date"]},
            document,
            upsert=True,
        )

    def bulk_upsert(self, documents: Sequence[dict[str, Any]], *, ordered: bool = False) -> int:
        return _bulk_replace(
            self.collection,
            documents,
            lambda doc: {"symbol": doc["symbol"], "trade_date": doc["trade_date"]},
            ordered=ordered,
        )


class AlgoResultRepository:
    def __init__(self, collection: Collection) -> None:
        self.collection = collection

    def upsert(
        self,
        algorithm: str,
        symbol: str,
        window_end_date: dt.date,
        payload: dict[str, Any],
        *,
        source_path: str | None = None,
    ) -> None:
        document = algo_result_document(
            algorithm,
            symbol,
            window_end_date,
            payload,
            source_path=source_path,
        )
        self.collection.replace_one(
            {
                "algorithm": document["algorithm"],
                "symbol": document["symbol"],
                "window_end_date": document["window_end_date"],
            },
            document,
            upsert=True,
        )

    def bulk_upsert(self, documents: Sequence[dict[str, Any]], *, ordered: bool = False) -> int:
        return _bulk_replace(
            self.collection,
            documents,
            lambda doc: {
                "algorithm": doc["algorithm"],
                "symbol": doc["symbol"],
                "window_end_date": doc["window_end_date"],
            },
            ordered=ordered,
        )


class RunSummaryRepository:
    def __init__(self, collection: Collection) -> None:
        self.collection = collection

    def upsert(
        self,
        kind: str,
        run_date: dt.date,
        payload: dict[str, Any],
        *,
        source_path: str | None = None,
    ) -> None:
        document = run_summary_document(kind, run_date, payload, source_path=source_path)
        filter_query = {
            "kind": document["kind"],
            "run_date": document["run_date"],
            "source_path": document["source_path"],
        }
        self.collection.replace_one(filter_query, document, upsert=True)

    def bulk_upsert(self, documents: Sequence[dict[str, Any]], *, ordered: bool = False) -> int:
        return _bulk_replace(
            self.collection,
            documents,
            lambda doc: {
                "kind": doc["kind"],
                "run_date": doc["run_date"],
                "source_path": doc["source_path"],
            },
            ordered=ordered,
        )


def chunked(items: Iterable[Any], size: int) -> Iterable[list[Any]]:
    batch: list[Any] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
