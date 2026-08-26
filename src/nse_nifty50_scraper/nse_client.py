from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import quote

import httpx

from nse_nifty50_scraper.config import SymbolConfig
from nse_nifty50_scraper.dates import format_nse_date

BASE_URL = "https://www.nseindia.com"
API_URL = f"{BASE_URL}/api/NextApi/apiClient/GetQuoteApi"


class NSEClientError(RuntimeError):
    pass


def browser_headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.8",
        "connection": "keep-alive",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
    }
    if referer:
        headers["referer"] = referer
    return headers


def quote_slug(symbol: SymbolConfig) -> str:
    if symbol.slug:
        return symbol.slug

    name = symbol.company_name
    name = re.sub(r"\b(Ltd|Limited|Company|Corporation|Corp)\.?\b", "", name, flags=re.I)
    name = re.sub(r"[^A-Za-z0-9]+", "-", name)
    return name.strip("-")


class NSEClient:
    def __init__(
        self,
        timeout: float = 20.0,
        retries: int = 2,
        retry_delay: float = 1.5,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers=browser_headers(BASE_URL),
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> NSEClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def warm_up_session(self, symbol: SymbolConfig | None = None) -> str:
        self._get(BASE_URL, referer=BASE_URL)
        time.sleep(0.4)

        if symbol is None:
            return BASE_URL

        quote_url = f"{BASE_URL}/get-quote/equity/{quote(symbol.symbol)}/{quote_slug(symbol)}"
        try:
            self._get(quote_url, referer=BASE_URL)
        except NSEClientError:
            # The API usually works after the homepage cookie warm-up. Some generated
            # quote slugs may not match NSE's exact route, so a failed quote page should
            # not block the data fetch.
            pass
        time.sleep(0.4)
        return quote_url

    def fetch_historical_data(
        self,
        symbol: SymbolConfig,
        from_date: Any,
        to_date: Any,
    ) -> Any:
        referer = self.warm_up_session(symbol)
        params = {
            "functionName": "getHistoricalTradeData",
            "symbol": symbol.symbol,
            "series": symbol.series,
            "fromDate": format_nse_date(from_date),
            "toDate": format_nse_date(to_date),
            "csv": "true",
        }
        response = self._get(API_URL, params=params, referer=referer)

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            sample = response.text[:300].replace("\n", " ")
            raise NSEClientError(f"NSE did not return JSON for {symbol.symbol}: {sample}") from exc

    def _get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                response = self.client.get(
                    url,
                    params=params,
                    headers=browser_headers(referer),
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in {401, 403, 429, 500, 502, 503, 504}:
                    break
            except httpx.HTTPError as exc:
                last_error = exc

            if attempt < self.retries:
                time.sleep(self.retry_delay * (attempt + 1))

        raise NSEClientError(f"Request failed for {url}: {last_error}") from last_error
