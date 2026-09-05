from __future__ import annotations

from types import TracebackType

from pymongo import MongoClient
from pymongo.database import Database

from nse_nifty50_scraper.db.settings import MongoSettings, load_mongo_settings


class MongoConnection:
    """Lazy Mongo client wrapper used by repositories and the seed CLI."""

    def __init__(self, settings: MongoSettings | None = None) -> None:
        self.settings = settings or load_mongo_settings()
        self._client: MongoClient | None = None

    @property
    def client(self) -> MongoClient:
        if self._client is None:
            self._client = MongoClient(
                self.settings.uri,
                connectTimeoutMS=self.settings.connect_timeout_ms,
                serverSelectionTimeoutMS=self.settings.server_selection_timeout_ms,
            )
        return self._client

    @property
    def db(self) -> Database:
        return self.client[self.settings.database]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> MongoConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


_connection: MongoConnection | None = None


def get_connection(settings: MongoSettings | None = None) -> MongoConnection:
    global _connection
    if _connection is None:
        _connection = MongoConnection(settings=settings)
    return _connection


def reset_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
