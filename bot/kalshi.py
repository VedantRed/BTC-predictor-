from __future__ import annotations

import base64
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class KalshiClient:
    def __init__(
        self,
        api_key_id: str | None,
        private_key_path: str | None,
        base_url: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key_id = api_key_id
        self._private_key = None
        if api_key_id and private_key_path:
            key_path = Path(private_key_path)
            if not key_path.exists():
                raise FileNotFoundError(f"Private key not found: {key_path}")
            self._private_key = serialization.load_pem_private_key(
                key_path.read_bytes(), password=None
            )

    @property
    def can_auth(self) -> bool:
        return self.api_key_id is not None and self._private_key is not None

    def _sign(self, method: str, path: str) -> dict[str, str]:
        if not self.can_auth:
            raise RuntimeError("Kalshi credentials are not configured")
        timestamp = str(int(time.time() * 1000))
        path_without_query = path.split("?")[0]
        message = f"{timestamp}{method}{path_without_query}".encode("utf-8")
        if isinstance(self._private_key, ed25519.Ed25519PrivateKey):
            signature = self._private_key.sign(message)
        else:
            signature = self._private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id or "",
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        auth: bool = False,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if auth:
            headers.update(self._sign("GET", path))
        response = requests.get(
            f"{self.base_url}{path}", params=params, headers=headers, timeout=15
        )
        response.raise_for_status()
        return response.json()

    def get_current_market(self, series_ticker: str) -> dict[str, Any]:
        data = self._get(
            "/trade-api/v2/markets",
            params={"series_ticker": series_ticker, "status": "open", "limit": 200},
        )
        markets = data.get("markets", [])
        now = datetime.now(timezone.utc)
        for market in markets:
            if market.get("status") not in ("active", "open"):
                continue
            try:
                open_time = parse_iso(market["open_time"])
                close_time = parse_iso(market["close_time"])
            except (KeyError, ValueError):
                continue
            if open_time <= now < close_time:
                return market
        if markets:
            return markets[0]
        raise RuntimeError(f"No open market found for series {series_ticker}")

    def get_orderbook(self, ticker: str) -> dict[str, list[list[float]]]:
        data = self._get(f"/trade-api/v2/markets/{ticker}/orderbook")
        fixed = data.get("orderbook_fp")
        if fixed is not None:
            yes = self._levels(fixed.get("yes_dollars") or fixed.get("yes"), 1.0)
            no = self._levels(fixed.get("no_dollars") or fixed.get("no"), 1.0)
        else:
            book = data.get("orderbook") or {}
            yes = self._levels(book.get("yes"), 0.01)
            no = self._levels(book.get("no"), 0.01)
        return {"yes_bids": yes, "no_bids": no}

    @staticmethod
    def _levels(raw: Any, scale: float) -> list[list[float]]:
        levels: list[list[float]] = []
        for item in raw or []:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                price, size = item[0], item[1]
            elif isinstance(item, dict):
                price = item.get("price") or item.get("price_dollars")
                size = item.get("size") or item.get("count") or item.get("size_fp")
            else:
                continue
            try:
                levels.append([float(price) * scale, float(size)])
            except (TypeError, ValueError):
                continue
        return levels

    def get_brti_values(self, index: str) -> list[tuple[datetime, float]]:
        data = self._get(
            "/trade-api/v2/cfbenchmarks/values", params={"id": index}, auth=True
        )
        body = data.get("data", data)
        payload = body.get("payload") if isinstance(body, dict) else body
        points: list[tuple[datetime, float]] = []

        if isinstance(payload, dict):
            iterable = payload.items()
        elif isinstance(payload, list):
            iterable = (
                (item.get("time") or item.get("timestamp"), item)
                for item in payload
                if isinstance(item, dict)
            )
        else:
            iterable = []

        for raw_time, raw_value in iterable:
            try:
                points.append(
                    (self._coerce_time(raw_time), self._coerce_value(raw_value))
                )
            except (TypeError, ValueError):
                continue
        points.sort(key=lambda point: point[0])
        return points

    @staticmethod
    def _coerce_value(raw: Any) -> float:
        if isinstance(raw, dict):
            value = raw.get("value")
            if value is None:
                value = raw.get("price")
            raw = value
        return float(raw)

    @staticmethod
    def _coerce_time(raw: Any) -> datetime:
        if isinstance(raw, (int, float)):
            value = float(raw)
            return datetime.fromtimestamp(
                value / 1000 if value > 1e11 else value, tz=timezone.utc
            )
        text = str(raw)
        if text.isdigit():
            value = int(text)
            return datetime.fromtimestamp(
                value / 1000 if value > 1e11 else value, tz=timezone.utc
            )
        return parse_iso(text)
