from __future__ import annotations

from pymongo import ASCENDING, IndexModel
from pymongo.database import Database

from nse_nifty50_scraper.db.settings import MongoSettings


def ensure_indexes(db: Database, settings: MongoSettings) -> None:
    """Create idempotent indexes for query and upsert performance."""
    db[settings.daily_bars_collection].create_indexes(
        [
            IndexModel(
                [("symbol", ASCENDING), ("trade_date", ASCENDING)],
                unique=True,
                name="uniq_symbol_trade_date",
            ),
            IndexModel([("trade_date", ASCENDING)], name="idx_trade_date"),
            IndexModel([("symbol", ASCENDING)], name="idx_symbol"),
        ]
    )
    db[settings.algo_results_collection].create_indexes(
        [
            IndexModel(
                [
                    ("algorithm", ASCENDING),
                    ("symbol", ASCENDING),
                    ("window_end_date", ASCENDING),
                ],
                unique=True,
                name="uniq_algo_symbol_window_end",
            ),
            IndexModel(
                [("algorithm", ASCENDING), ("window_end_date", ASCENDING)],
                name="idx_algo_window_end",
            ),
        ]
    )
    db[settings.runs_collection].create_indexes(
        [
            IndexModel(
                [("kind", ASCENDING), ("run_date", ASCENDING), ("source_path", ASCENDING)],
                unique=True,
                name="uniq_kind_run_date_source",
            ),
            IndexModel([("run_date", ASCENDING)], name="idx_run_date"),
        ]
    )
