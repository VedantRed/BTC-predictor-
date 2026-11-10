from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .kalshi import parse_iso


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _top(levels: list[list[float]], count: int = 5) -> list[dict[str, float]]:
    ordered = sorted(levels, key=lambda level: level[0], reverse=True)[:count]
    return [
        {"price": round(price, 4), "size": round(size, 2)}
        for price, size in ordered
    ]


def _asks_from_bids(
    bids: list[list[float]], count: int = 5
) -> list[dict[str, float]]:
    asks = [[1.0 - price, size] for price, size in bids]
    asks.sort(key=lambda level: level[0])
    return [
        {"price": round(price, 4), "size": round(size, 2)}
        for price, size in asks[:count]
    ]


def _window_stats(
    points: list[tuple[datetime, float]], now: datetime, window: timedelta
) -> dict[str, float] | None:
    cutoff = now - window
    values = [value for timestamp, value in points if timestamp >= cutoff]
    if not values:
        return None
    return {
        "avg": sum(values) / len(values),
        "high": max(values),
        "low": min(values),
        "count": len(values),
    }


def build_state(
    market: dict[str, Any],
    orderbook: dict[str, list[list[float]]],
    brti_points: list[tuple[datetime, float]],
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    open_time = parse_iso(market["open_time"])
    close_time = parse_iso(market["close_time"])
    target = _float(market.get("floor_strike"))

    yes_bids = orderbook.get("yes_bids", [])
    no_bids = orderbook.get("no_bids", [])

    yes_bid = max((price for price, _ in yes_bids), default=None)
    no_bid = max((price for price, _ in no_bids), default=None)

    if yes_bid is None:
        yes_bid = _float(market.get("yes_bid_dollars"))
    if no_bid is None:
        no_bid = _float(market.get("no_bid_dollars"))
    yes_ask = (
        1.0 - no_bid
        if no_bid is not None
        else _float(market.get("yes_ask_dollars"))
    )
    no_ask = (
        1.0 - yes_bid
        if yes_bid is not None
        else _float(market.get("no_ask_dollars"))
    )

    last = max(brti_points, key=lambda point: point[0])[1] if brti_points else None
    stats_60s = _window_stats(brti_points, now, timedelta(seconds=60))
    stats_30m = _window_stats(brti_points, now, timedelta(minutes=30))

    def dist_bps(value: float | None) -> float | None:
        if value is None or not target:
            return None
        return round((value - target) / target * 10_000, 2)

    return {
        "generated_at": now.isoformat(),
        "market": {
            "ticker": market.get("ticker"),
            "title": market.get("title"),
            "target": target,
            "strike_type": market.get("strike_type"),
            "open_time": market.get("open_time"),
            "close_time": market.get("close_time"),
            "seconds_into_window": round(
                max(0.0, (now - open_time).total_seconds()), 1
            ),
            "seconds_to_close": round((close_time - now).total_seconds(), 1),
        },
        "price": {
            "brti_last": round(last, 2) if last is not None else None,
            "brti_avg_60s": round(stats_60s["avg"], 2) if stats_60s else None,
            "brti_avg_30m": round(stats_30m["avg"], 2) if stats_30m else None,
            "brti_high_30m": round(stats_30m["high"], 2) if stats_30m else None,
            "brti_low_30m": round(stats_30m["low"], 2) if stats_30m else None,
            "dist_last_bps": dist_bps(last),
            "dist_60s_bps": dist_bps(stats_60s["avg"] if stats_60s else None),
            "dist_30m_avg_bps": dist_bps(stats_30m["avg"] if stats_30m else None),
        },
        "book": {
            "yes_bid": round(yes_bid, 4) if yes_bid is not None else None,
            "yes_ask": round(yes_ask, 4) if yes_ask is not None else None,
            "no_bid": round(no_bid, 4) if no_bid is not None else None,
            "no_ask": round(no_ask, 4) if no_ask is not None else None,
            "spread": (
                round(yes_ask - yes_bid, 4)
                if yes_ask is not None and yes_bid is not None
                else None
            ),
            "yes_bids": _top(yes_bids),
            "no_bids": _top(no_bids),
            "yes_asks": _asks_from_bids(no_bids),
            "no_asks": _asks_from_bids(yes_bids),
        },
    }
