from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from typing import Any

from nse_nifty50_scraper.db.connection import MongoConnection, get_connection, reset_connection
from nse_nifty50_scraper.db.indexes import ensure_indexes
from nse_nifty50_scraper.db.repositories import (
    AlgoResultRepository,
    DailyBarRepository,
    RunSummaryRepository,
)
from nse_nifty50_scraper.db.settings import (
    MongoSettings,
    clear_mongo_settings_cache,
    load_mongo_settings,
)

logger = logging.getLogger(__name__)

_store: MongoStore | None = None
_store_checked = False


class MongoStore:
    """Facade over Mongo repositories with index bootstrap."""

    def __init__(self, connection: MongoConnection, settings: MongoSettings | None = None) -> None:
        self.connection = connection
        self.settings = settings or connection.settings
        self.daily_bars = DailyBarRepository(connection.db[self.settings.daily_bars_collection])
        self.algo_results = AlgoResultRepository(
            connection.db[self.settings.algo_results_collection]
        )
        self.runs = RunSummaryRepository(connection.db[self.settings.runs_collection])
        self._indexes_ready = False

    def ensure_ready(self) -> None:
        if self._indexes_ready:
            return
        ensure_indexes(self.connection.db, self.settings)
        self._indexes_ready = True

    def upsert_daily_bar(
        self,
        symbol: str,
        trade_date: dt.date,
        payload: dict[str, Any],
        *,
        source_path: str | None = None,
    ) -> None:
        self.ensure_ready()
        self.daily_bars.upsert(symbol, trade_date, payload, source_path=source_path)

    def upsert_algo_result(
        self,
        algorithm: str,
        symbol: str,
        window_end_date: dt.date,
        payload: dict[str, Any],
        *,
        source_path: str | None = None,
    ) -> None:
        self.ensure_ready()
        self.algo_results.upsert(
            algorithm,
            symbol,
            window_end_date,
            payload,
            source_path=source_path,
        )

    def upsert_run_summary(
        self,
        kind: str,
        run_date: dt.date,
        payload: dict[str, Any],
        *,
        source_path: str | None = None,
    ) -> None:
        self.ensure_ready()
        self.runs.upsert(kind, run_date, payload, source_path=source_path)


def get_mongo_store(*, force_reload: bool = False) -> MongoStore | None:
    """
    Return a shared MongoStore when Mongo is enabled, otherwise None.

    Callers should treat None as "JSON-only mode".
    """
    global _store, _store_checked

    if force_reload:
        reset_mongo_store()

    if _store_checked and not force_reload:
        return _store

    settings = load_mongo_settings()
    _store_checked = True
    if not settings.enabled:
        _store = None
        return None

    connection = get_connection(settings)
    _store = MongoStore(connection, settings=settings)
    return _store


def reset_mongo_store() -> None:
    global _store, _store_checked
    reset_connection()
    clear_mongo_settings_cache()
    _store = None
    _store_checked = False


def mongo_write(operation_name: str, callback: Callable[[MongoStore], None]) -> None:
    """Run a Mongo write and optionally swallow failures unless strict mode is on."""
    store = get_mongo_store()
    if store is None:
        return

    try:
        callback(store)
    except Exception as exc:
        settings = store.settings
        message = f"Mongo {operation_name} failed: {exc}"
        if settings.strict:
            raise RuntimeError(message) from exc
        logger.warning(message)
