from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field


class MongoSettings(BaseModel):
    """Runtime MongoDB settings loaded from environment variables."""

    enabled: bool = False
    uri: str = "mongodb://localhost:27017"
    database: str = "nse_scanner"
    daily_bars_collection: str = "daily_bars"
    algo_results_collection: str = "algo_results"
    runs_collection: str = "runs"
    connect_timeout_ms: int = Field(default=5_000, ge=100)
    server_selection_timeout_ms: int = Field(default=5_000, ge=100)
    strict: bool = False


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def load_mongo_settings() -> MongoSettings:
    """
    Load Mongo settings.

    Mongo is enabled when MONGO_ENABLED=true, or when MONGO_URI is explicitly set.
    """
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017").strip()
    enabled_explicit = os.getenv("MONGO_ENABLED")
    if enabled_explicit is not None:
        enabled = _env_bool("MONGO_ENABLED")
    else:
        enabled = "MONGO_URI" in os.environ

    return MongoSettings(
        enabled=enabled,
        uri=uri,
        database=os.getenv("MONGO_DB", "nse_scanner").strip() or "nse_scanner",
        daily_bars_collection=os.getenv("MONGO_DAILY_BARS_COLLECTION", "daily_bars").strip(),
        algo_results_collection=os.getenv("MONGO_ALGO_RESULTS_COLLECTION", "algo_results").strip(),
        runs_collection=os.getenv("MONGO_RUNS_COLLECTION", "runs").strip(),
        connect_timeout_ms=int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000")),
        server_selection_timeout_ms=int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")),
        strict=_env_bool("MONGO_STRICT"),
    )


def clear_mongo_settings_cache() -> None:
    load_mongo_settings.cache_clear()
