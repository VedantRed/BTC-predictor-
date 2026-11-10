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
    typesafe_api_key: str | None
    typesafe_base_url: str
    typesafe_model: str
    entry_start_seconds: int
    entry_end_seconds: int
    up_threshold: float
    down_threshold: float


def load_config() -> Config:
    return Config(
        api_key_id=os.getenv("KALSHI_API_KEY_ID") or None,
        private_key_path=os.getenv("KALSHI_PRIVATE_KEY_PATH") or None,
        base_url=os.getenv("KALSHI_BASE_URL", "https://external-api.kalshi.com"),
        series_ticker=os.getenv("KALSHI_SERIES", "KXBTC15M"),
        brti_index=os.getenv("BRTI_INDEX", "BRTI"),
        typesafe_api_key=os.getenv("TYPESAFE_API_KEY") or None,
        typesafe_base_url=os.getenv(
            "TYPESAFE_BASE_URL", "https://api.typesafe.ai"
        ),
        typesafe_model=os.getenv("TYPESAFE_MODEL", "jev-latest"),
        entry_start_seconds=int(os.getenv("ENTRY_START_SECONDS", "120")),
        entry_end_seconds=int(os.getenv("ENTRY_END_SECONDS", "360")),
        up_threshold=float(os.getenv("UP_THRESHOLD", "0.75")),
        down_threshold=float(os.getenv("DOWN_THRESHOLD", "0.25")),
    )
