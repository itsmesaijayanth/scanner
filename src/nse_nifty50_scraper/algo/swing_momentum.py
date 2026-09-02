from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from nse_nifty50_scraper.algo.models import DailyRow
from nse_nifty50_scraper.dates import format_nse_date

ALGORITHM_NAME = "swing_momentum"
ALGORITHM_VERSION = "0.1.0"
TrendDirection = Literal["UpTrend", "DownTrend", "Sideways", "InsufficientData"]


def almost_equal(left: float, right: float, tolerance: float) -> bool:
    return abs(left - right) <= tolerance


def latest_row_on_or_before(rows: list[DailyRow], end_date: dt.date | None) -> DailyRow | None:
    if not rows:
        return None
    if end_date is None:
        return rows[-1]

    eligible = [row for row in rows if row.date <= end_date]
    if not eligible:
        return None
    return eligible[-1]


def choose_latest_max(rows: list[DailyRow]) -> tuple[int, DailyRow]:
    max_high = max(row.high for row in rows)
    matches = [(index, row) for index, row in enumerate(rows) if row.high == max_high]
    return matches[-1]


def choose_latest_min(rows: list[DailyRow]) -> tuple[int, DailyRow]:
    min_low = min(row.low for row in rows)
    matches = [(index, row) for index, row in enumerate(rows) if row.low == min_low]
    return matches[-1]


def signal_type(row: DailyRow, tolerance: float) -> str | None:
    bearish = almost_equal(row.open, row.high, tolerance)
    bullish = almost_equal(row.open, row.low, tolerance)
    if bearish and bullish:
        return "conflicting_momentum"
    if bearish:
        return "bearish_momentum"
    if bullish:
        return "bullish_momentum"
    return None


def signal_events(rows: list[DailyRow], tolerance: float) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in rows:
        signal = signal_type(row, tolerance)
        if signal is None:
            continue

        if signal == "bearish_momentum":
            rule = "open_equals_high"
        elif signal == "bullish_momentum":
            rule = "open_equals_low"
        else:
            rule = "open_equals_high_and_low"

        events.append(
            {
                "date": format_nse_date(row.date),
                "type": signal,
                "rule": rule,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
            }
        )
    return events


def signal_strength(
    rows: list[DailyRow],
    events: list[dict[str, Any]],
    active_signal: str | None,
) -> str:
    if active_signal is None:
        return "none"

    matching_dates = {
        event["date"]
        for event in events
        if event["type"] in {active_signal, "conflicting_momentum"}
    }
    if not matching_dates:
        return "none"

    current_index = len(rows) - 1
    latest_distance = min(
        current_index - index
        for index, row in enumerate(rows)
        if format_nse_date(row.date) in matching_dates
    )
    if latest_distance == 0:
        return "strong"
    if latest_distance <= 2:
        return "recent"
    return "weak"


def determine_trend(
    high_distance: int,
    low_distance: int,
    current_signal: str | None,
) -> tuple[TrendDirection, str]:
    if high_distance < low_distance:
        return "DownTrend", "monthly_high_is_closer_to_current_day"
    if low_distance < high_distance:
        return "UpTrend", "monthly_low_is_closer_to_current_day"
    if current_signal == "bullish_momentum":
        return "UpTrend", "equal_extreme_distance_with_current_bullish_signal"
    if current_signal == "bearish_momentum":
        return "DownTrend", "equal_extreme_distance_with_current_bearish_signal"
    return "Sideways", "monthly_high_and_low_are_equally_close"


def active_signal_for_trend(trend: TrendDirection, events: list[dict[str, Any]]) -> str | None:
    if trend == "UpTrend":
        return (
            "bullish_momentum"
            if any(event["type"] == "bullish_momentum" for event in events)
            else None
        )
    if trend == "DownTrend":
        return (
            "bearish_momentum"
            if any(event["type"] == "bearish_momentum" for event in events)
            else None
        )

    if events and events[-1]["type"] != "conflicting_momentum":
        return str(events[-1]["type"])
    return None


def verdict_state(
    trend: TrendDirection, active_signal: str | None, strength: str
) -> tuple[str, str]:
    if trend == "InsufficientData":
        return "insufficient_data", "none"
    if trend == "Sideways":
        return "sideways", "low"

    aligned = (trend == "UpTrend" and active_signal == "bullish_momentum") or (
        trend == "DownTrend" and active_signal == "bearish_momentum"
    )
    if aligned and strength == "strong":
        return f"confirmed_{trend.lower()}", "high"
    if aligned and strength == "recent":
        return f"confirmed_{trend.lower()}", "medium"
    if aligned:
        return f"weakly_confirmed_{trend.lower()}", "low"
    return f"unconfirmed_{trend.lower()}", "low"


def analyze_swing_momentum(
    symbol: str,
    rows: list[DailyRow],
    end_date: dt.date | None = None,
    window_days: int = 30,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    sorted_rows = sorted(rows, key=lambda row: row.date)
    current = latest_row_on_or_before(sorted_rows, end_date)
    if current is None:
        return insufficient_output(symbol, end_date, window_days, "No rows available")

    window_start = current.date - dt.timedelta(days=window_days)
    window_rows = [row for row in sorted_rows if window_start <= row.date <= current.date]
    if len(window_rows) < 2:
        return insufficient_output(
            symbol,
            current.date,
            window_days,
            "At least two trading rows are required",
            window_rows,
        )

    high_index, high_row = choose_latest_max(window_rows)
    low_index, low_row = choose_latest_min(window_rows)
    current_index = len(window_rows) - 1
    high_distance = current_index - high_index
    low_distance = current_index - low_index
    current_signal = signal_type(current, tolerance)
    trend, reason = determine_trend(high_distance, low_distance, current_signal)
    events = signal_events(window_rows, tolerance)
    active_signal = active_signal_for_trend(trend, events)
    strength = signal_strength(window_rows, events, active_signal)
    state, confidence = verdict_state(trend, active_signal, strength)

    if trend == "UpTrend":
        target_reference = {"label": "monthly_high", "price": high_row.high}
        opposite_extreme = {"label": "monthly_low", "price": low_row.low}
        expected_zone = "monthly_high"
    elif trend == "DownTrend":
        target_reference = {"label": "monthly_low", "price": low_row.low}
        opposite_extreme = {"label": "monthly_high", "price": high_row.high}
        expected_zone = "monthly_low"
    else:
        target_reference = {"label": "none", "price": None}
        opposite_extreme = {"label": "none", "price": None}
        expected_zone = "none"

    notes = [f"Trend is {trend} because {reason}."]
    if active_signal:
        notes.append(f"Active signal is {active_signal} with {strength} strength.")
    else:
        notes.append("No active momentum signal aligned with the trend.")

    return {
        "algorithm": ALGORITHM_NAME,
        "version": ALGORITHM_VERSION,
        "symbol": symbol.upper(),
        "window": {
            "start_date": format_nse_date(window_start),
            "end_date": format_nse_date(current.date),
            "calendar_days": window_days,
            "trading_rows": len(window_rows),
        },
        "trend": {
            "direction": trend,
            "reason": reason,
            "monthly_high": {
                "date": format_nse_date(high_row.date),
                "price": high_row.high,
                "distance_to_current_trading_rows": high_distance,
            },
            "monthly_low": {
                "date": format_nse_date(low_row.date),
                "price": low_row.low,
                "distance_to_current_trading_rows": low_distance,
            },
            "current": current.compact(),
        },
        "signals": {
            "active_signal": active_signal,
            "strength": strength,
            "events": events,
        },
        "levels": {
            "expected_next_zone": expected_zone,
            "target_reference": target_reference,
            "opposite_extreme": opposite_extreme,
            "risk_reference": opposite_extreme,
        },
        "verdict": {
            "state": state,
            "confidence": confidence,
            "notes": notes,
        },
        "source_rows": [row.compact() for row in window_rows],
    }


def insufficient_output(
    symbol: str,
    end_date: dt.date | None,
    window_days: int,
    reason: str,
    rows: list[DailyRow] | None = None,
) -> dict[str, Any]:
    rows = rows or []
    return {
        "algorithm": ALGORITHM_NAME,
        "version": ALGORITHM_VERSION,
        "symbol": symbol.upper(),
        "window": {
            "start_date": None,
            "end_date": format_nse_date(end_date) if end_date else None,
            "calendar_days": window_days,
            "trading_rows": len(rows),
        },
        "trend": {
            "direction": "InsufficientData",
            "reason": reason,
        },
        "signals": {
            "active_signal": None,
            "strength": "none",
            "events": [],
        },
        "levels": {
            "expected_next_zone": "none",
            "target_reference": {"label": "none", "price": None},
            "opposite_extreme": {"label": "none", "price": None},
            "risk_reference": {"label": "none", "price": None},
        },
        "verdict": {
            "state": "insufficient_data",
            "confidence": "none",
            "notes": [reason],
        },
        "source_rows": [row.compact() for row in rows],
    }
