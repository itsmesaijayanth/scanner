from __future__ import annotations

import os
from unittest.mock import patch

from nse_nifty50_scraper.db.settings import clear_mongo_settings_cache, load_mongo_settings


def teardown_function() -> None:
    clear_mongo_settings_cache()


def test_mongo_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.delenv("MONGO_ENABLED", raising=False)
    clear_mongo_settings_cache()

    settings = load_mongo_settings()

    assert settings.enabled is False
    assert settings.database == "nse_scanner"


def test_mongo_enabled_when_uri_set(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://example:27017")
    monkeypatch.delenv("MONGO_ENABLED", raising=False)
    clear_mongo_settings_cache()

    settings = load_mongo_settings()

    assert settings.enabled is True
    assert settings.uri == "mongodb://example:27017"


def test_mongo_enabled_flag_overrides_missing_uri(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setenv("MONGO_ENABLED", "true")
    monkeypatch.setenv("MONGO_DB", "scanner_test")
    clear_mongo_settings_cache()

    settings = load_mongo_settings()

    assert settings.enabled is True
    assert settings.database == "scanner_test"


def test_settings_cache_clears(monkeypatch):
    monkeypatch.setenv("MONGO_ENABLED", "false")
    clear_mongo_settings_cache()
    first = load_mongo_settings()
    monkeypatch.setenv("MONGO_ENABLED", "true")
    with patch.dict(os.environ, {"MONGO_ENABLED": "true"}):
        clear_mongo_settings_cache()
        second = load_mongo_settings()

    assert first.enabled is False
    assert second.enabled is True
