from __future__ import annotations

import math
from typing import Any

from .config import Config


def taker_fee(price: float, contracts: int = 1) -> float:
    raw = 0.07 * contracts * price * (1 - price)
    return math.ceil(raw * 100) / 100


def decide(
    state: dict[str, Any], probability_up: float, config: Config
) -> dict[str, Any]:
    seconds = state["market"]["seconds_into_window"]
    book = state["book"]
    result: dict[str, Any] = {
        "probability_up": round(probability_up, 4),
        "in_entry_window": False,
        "action": "wait",
        "reason": "",
    }

    in_window = (
        config.entry_start_seconds <= seconds <= config.entry_end_seconds
    )
    result["in_entry_window"] = in_window
    if not in_window:
        result["reason"] = (
            f"outside entry window ({config.entry_start_seconds}-"
            f"{config.entry_end_seconds}s into window; now {seconds:.0f}s)"
        )
        return result

    if probability_up > config.up_threshold:
        ask = book.get("yes_ask")
        if ask is None:
            result["reason"] = "no YES ask available"
            return result
        fee = taker_fee(ask)
        edge = probability_up - ask - fee
        result.update(
            {"side": "yes", "ask": ask, "fee": fee, "edge": round(edge, 4)}
        )
        if edge > 0:
            result["action"] = "buy_yes"
            result["reason"] = "probability above threshold and positive edge"
        else:
            result["reason"] = "no positive edge after fee"
        return result

    if probability_up < config.down_threshold:
        ask = book.get("no_ask")
        if ask is None:
            result["reason"] = "no NO ask available"
            return result
        fee = taker_fee(ask)
        edge = (1 - probability_up) - ask - fee
        result.update(
            {"side": "no", "ask": ask, "fee": fee, "edge": round(edge, 4)}
        )
        if edge > 0:
            result["action"] = "buy_no"
            result["reason"] = "probability below threshold and positive edge"
        else:
            result["reason"] = "no positive edge after fee"
        return result

    result["reason"] = (
        f"probability {probability_up:.3f} between "
        f"{config.down_threshold} and {config.up_threshold}"
    )
    return result
