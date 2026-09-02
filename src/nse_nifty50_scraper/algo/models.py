from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from nse_nifty50_scraper.dates import format_nse_date, parse_nse_timestamp


class DailyRowError(ValueError):
    pass


@dataclass(frozen=True)
class DailyRow:
    symbol: str
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    raw: dict[str, Any]

    @classmethod
    def from_nse(cls, data: dict[str, Any]) -> DailyRow:
        try:
            symbol = str(data["chSymbol"]).upper()
            timestamp = str(data["mtimestamp"])
            return cls(
                symbol=symbol,
                date=parse_nse_timestamp(timestamp),
                open=float(data["chOpeningPrice"]),
                high=float(data["chTradeHighPrice"]),
                low=float(data["chTradeLowPrice"]),
                close=float(data["chClosingPrice"]),
                raw=data,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DailyRowError(f"Invalid NSE daily row: {exc}") from exc

    def compact(self) -> dict[str, Any]:
        return {
            "date": format_nse_date(self.date),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }
