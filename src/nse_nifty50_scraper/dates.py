from __future__ import annotations

import datetime as dt

from dateutil.tz import gettz

IST = gettz("Asia/Kolkata")
NSE_DATE_FORMAT = "%d-%m-%Y"


def today_ist() -> dt.date:
    return dt.datetime.now(tz=IST).date()


def parse_nse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, NSE_DATE_FORMAT).date()


def format_nse_date(value: dt.date) -> str:
    return value.strftime(NSE_DATE_FORMAT)


def rolling_window(days: int, end_date: dt.date | None = None) -> tuple[dt.date, dt.date]:
    if days < 1:
        raise ValueError("days must be at least 1")

    end = end_date or today_ist()
    start = end - dt.timedelta(days=days)
    return start, end
