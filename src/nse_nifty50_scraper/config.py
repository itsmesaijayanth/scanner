from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "nifty50.json"


class SymbolConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    symbol: str = Field(min_length=1)
    series: str = Field(default="EQ", min_length=1)
    company_name: str = Field(min_length=1)
    industry: str | None = None
    isin: str | None = None
    slug: str | None = None

    @field_validator("symbol", "series")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.upper()


def load_symbols(config_path: Path = DEFAULT_CONFIG_PATH) -> list[SymbolConfig]:
    with config_path.open(encoding="utf-8") as file:
        data = json.load(file)

    symbols = [SymbolConfig.model_validate(item) for item in data]
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in symbols:
        if item.symbol in seen:
            duplicates.append(item.symbol)
        seen.add(item.symbol)

    if duplicates:
        names = ", ".join(sorted(set(duplicates)))
        raise ValueError(f"Duplicate symbols in config: {names}")

    return symbols


def filter_symbols(
    symbols: list[SymbolConfig],
    requested: list[str] | None,
) -> list[SymbolConfig]:
    if not requested:
        return symbols

    wanted = {symbol.upper().strip() for symbol in requested}
    selected = [symbol for symbol in symbols if symbol.symbol in wanted]
    found = {symbol.symbol for symbol in selected}
    missing = sorted(wanted - found)
    if missing:
        raise ValueError(f"Symbols not found in config: {', '.join(missing)}")

    return selected
