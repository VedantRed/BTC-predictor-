from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    api_key_id: str | None
    private_key_path: str | None
    base_url: str
    series_ticker: str
    brti_index: str


def load_config() -> Config:
    return Config(
        api_key_id=os.getenv("KALSHI_API_KEY_ID") or None,
        private_key_path=os.getenv("KALSHI_PRIVATE_KEY_PATH") or None,
        base_url=os.getenv("KALSHI_BASE_URL", "https://external-api.kalshi.com"),
        series_ticker=os.getenv("KALSHI_SERIES", "KXBTC15M"),
        brti_index=os.getenv("BRTI_INDEX", "BRTI"),
    )
