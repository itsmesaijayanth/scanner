from __future__ import annotations

import datetime as dt

from dateutil.tz import gettz

IST = gettz("Asia/Kolkata")
NSE_DATE_FORMAT = "%d-%m-%Y"
NSE_TIMESTAMP_FORMAT = "%d-%b-%Y"
MONTH_ABBR = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def today_ist() -> dt.date:
    return dt.datetime.now(tz=IST).date()


def parse_nse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, NSE_DATE_FORMAT).date()


def format_nse_date(value: dt.date) -> str:
    return value.strftime(NSE_DATE_FORMAT)


def parse_nse_timestamp(value: str) -> dt.date:
    return dt.datetime.strptime(value, NSE_TIMESTAMP_FORMAT).date()


def date_path_parts(value: dt.date) -> tuple[str, str, str]:
    return str(value.year), MONTH_ABBR[value.month], f"{value.day:02d}"


def rolling_window(days: int, end_date: dt.date | None = None) -> tuple[dt.date, dt.date]:
    if days < 1:
        raise ValueError("days must be at least 1")

    end = end_date or today_ist()
    start = end - dt.timedelta(days=days)
    return start, end
