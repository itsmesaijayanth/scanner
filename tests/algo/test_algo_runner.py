from __future__ import annotations

import datetime as dt

from nse_nifty50_scraper.algo.runner import backfill_swing_momentum, run_swing_momentum
from nse_nifty50_scraper.config import SymbolConfig
from nse_nifty50_scraper.runner import write_json


def test_run_swing_momentum_writes_window_response(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "algo"
    runs_dir = tmp_path / "runs"
    write_json(
        raw_dir / "SBIN" / "2026" / "Aug" / "01" / "response.json",
        {
            "chSymbol": "SBIN",
            "mtimestamp": "01-Aug-2026",
            "chOpeningPrice": 100,
            "chTradeHighPrice": 105,
            "chTradeLowPrice": 99,
            "chClosingPrice": 104,
        },
    )
    write_json(
        raw_dir / "SBIN" / "2026" / "Aug" / "02" / "response.json",
        {
            "chSymbol": "SBIN",
            "mtimestamp": "02-Aug-2026",
            "chOpeningPrice": 104,
            "chTradeHighPrice": 108,
            "chTradeLowPrice": 103,
            "chClosingPrice": 107,
        },
    )

    result = run_swing_momentum(
        symbols=[SymbolConfig(symbol="SBIN", series="EQ", company_name="State Bank of India")],
        raw_dir=raw_dir,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=dt.date(2026, 8, 3),
    )

    assert result.succeeded == 1
    assert (
        output_dir / "swing_momentum" / "SBIN" / "2026" / "Aug" / "02" / "window" / "response.json"
    ).exists()


def _write_sbin_rows(raw_dir, rows: list[tuple[str, float, float, float, float]]) -> None:
    for date, open_, high, low, close in rows:
        day, month, year = date.split("-")
        write_json(
            raw_dir / "SBIN" / year / month / day / "response.json",
            {
                "chSymbol": "SBIN",
                "mtimestamp": date,
                "chOpeningPrice": open_,
                "chTradeHighPrice": high,
                "chTradeLowPrice": low,
                "chClosingPrice": close,
            },
        )


def test_run_swing_momentum_skips_existing_output(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "algo"
    runs_dir = tmp_path / "runs"
    _write_sbin_rows(
        raw_dir,
        [
            ("01-Aug-2026", 100, 105, 99, 104),
            ("02-Aug-2026", 104, 108, 103, 107),
        ],
    )

    symbol = SymbolConfig(symbol="SBIN", series="EQ", company_name="State Bank of India")
    run_swing_momentum(
        symbols=[symbol],
        raw_dir=raw_dir,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=dt.date(2026, 8, 3),
    )
    result = run_swing_momentum(
        symbols=[symbol],
        raw_dir=raw_dir,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=dt.date(2026, 8, 3),
        skip_existing=True,
    )

    assert result.skipped == 1
    assert result.succeeded == 0


def test_backfill_swing_momentum_processes_all_trading_dates(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "algo"
    runs_dir = tmp_path / "runs"
    _write_sbin_rows(
        raw_dir,
        [
            ("01-Aug-2026", 100, 105, 99, 104),
            ("02-Aug-2026", 104, 108, 103, 107),
            ("03-Aug-2026", 107, 110, 106, 109),
        ],
    )

    symbol = SymbolConfig(symbol="SBIN", series="EQ", company_name="State Bank of India")
    result = backfill_swing_momentum(
        symbols=[symbol],
        raw_dir=raw_dir,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=dt.date(2026, 8, 4),
        window_days=30,
    )

    assert result.dates_total == 3
    assert result.dates_processed == 3
    assert result.dates_skipped == 0
    assert result.succeeded == 3
    assert (
        output_dir / "swing_momentum" / "SBIN" / "2026" / "Aug" / "01" / "window" / "response.json"
    ).exists()
    assert (runs_dir / "swing_momentum-backfill-04-08-2026.json").exists()


def test_backfill_swing_momentum_resumes_existing_outputs(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "algo"
    runs_dir = tmp_path / "runs"
    _write_sbin_rows(
        raw_dir,
        [
            ("01-Aug-2026", 100, 105, 99, 104),
            ("02-Aug-2026", 104, 108, 103, 107),
        ],
    )

    symbol = SymbolConfig(symbol="SBIN", series="EQ", company_name="State Bank of India")
    first = backfill_swing_momentum(
        symbols=[symbol],
        raw_dir=raw_dir,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=dt.date(2026, 8, 3),
    )
    second = backfill_swing_momentum(
        symbols=[symbol],
        raw_dir=raw_dir,
        output_dir=output_dir,
        runs_dir=runs_dir,
        run_date=dt.date(2026, 8, 3),
        skip_existing=True,
    )

    assert first.succeeded == 2
    assert second.dates_skipped == 2
    assert second.succeeded == 0
    assert second.skipped == 2
