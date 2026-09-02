from __future__ import annotations

from nse_nifty50_scraper.algo.models import DailyRow
from nse_nifty50_scraper.algo.swing_momentum import analyze_swing_momentum


def row(date: str, open_: float, high: float, low: float, close: float) -> DailyRow:
    return DailyRow.from_nse(
        {
            "chSymbol": "SBIN",
            "mtimestamp": date,
            "chOpeningPrice": open_,
            "chTradeHighPrice": high,
            "chTradeLowPrice": low,
            "chClosingPrice": close,
        }
    )


def test_downtrend_with_current_open_equals_high_is_confirmed():
    analysis = analyze_swing_momentum(
        "SBIN",
        [
            row("01-Aug-2026", 100, 102, 98, 101),
            row("10-Aug-2026", 110, 115, 108, 114),
            row("20-Aug-2026", 112, 116, 109, 111),
            row("26-Aug-2026", 110, 110, 103, 104),
        ],
    )

    assert analysis["trend"]["direction"] == "DownTrend"
    assert analysis["signals"]["active_signal"] == "bearish_momentum"
    assert analysis["signals"]["strength"] == "strong"
    assert analysis["levels"]["target_reference"]["label"] == "monthly_low"


def test_uptrend_with_recent_open_equals_low_is_confirmed():
    analysis = analyze_swing_momentum(
        "SBIN",
        [
            row("01-Aug-2026", 110, 120, 108, 111),
            row("10-Aug-2026", 100, 104, 95, 103),
            row("24-Aug-2026", 104, 110, 104, 109),
            row("26-Aug-2026", 108, 114, 107, 113),
        ],
    )

    assert analysis["trend"]["direction"] == "UpTrend"
    assert analysis["signals"]["active_signal"] == "bullish_momentum"
    assert analysis["signals"]["strength"] == "recent"
    assert analysis["levels"]["target_reference"]["label"] == "monthly_high"


def test_holiday_end_date_uses_latest_available_trading_row():
    analysis = analyze_swing_momentum(
        "SBIN",
        [
            row("01-Sep-2026", 100, 105, 99, 104),
            row("02-Sep-2026", 104, 108, 103, 107),
        ],
        end_date=row("03-Sep-2026", 1, 1, 1, 1).date,
    )

    assert analysis["window"]["end_date"] == "02-09-2026"


def test_insufficient_data_when_window_has_one_row():
    analysis = analyze_swing_momentum("SBIN", [row("01-Sep-2026", 100, 101, 99, 100)])

    assert analysis["trend"]["direction"] == "InsufficientData"
    assert analysis["verdict"]["state"] == "insufficient_data"
