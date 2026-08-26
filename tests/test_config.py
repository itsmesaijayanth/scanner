from __future__ import annotations

import json

import pytest

from nse_nifty50_scraper.config import filter_symbols, load_symbols


def test_load_symbols_validates_and_uppercases(tmp_path):
    config = tmp_path / "symbols.json"
    config.write_text(
        json.dumps(
            [
                {
                    "symbol": "sbin",
                    "series": "eq",
                    "company_name": "State Bank of India",
                }
            ]
        ),
        encoding="utf-8",
    )

    symbols = load_symbols(config)

    assert symbols[0].symbol == "SBIN"
    assert symbols[0].series == "EQ"


def test_load_symbols_rejects_duplicates(tmp_path):
    config = tmp_path / "symbols.json"
    config.write_text(
        json.dumps(
            [
                {"symbol": "SBIN", "series": "EQ", "company_name": "State Bank of India"},
                {"symbol": "sbin", "series": "EQ", "company_name": "State Bank of India"},
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate symbols"):
        load_symbols(config)


def test_filter_symbols_returns_requested_items(tmp_path):
    config = tmp_path / "symbols.json"
    config.write_text(
        json.dumps(
            [
                {"symbol": "SBIN", "series": "EQ", "company_name": "State Bank of India"},
                {"symbol": "TCS", "series": "EQ", "company_name": "Tata Consultancy Services"},
            ]
        ),
        encoding="utf-8",
    )
    symbols = load_symbols(config)

    selected = filter_symbols(symbols, ["tcs"])

    assert [item.symbol for item in selected] == ["TCS"]
