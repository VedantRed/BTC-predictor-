from __future__ import annotations

import json

from bot.config import load_config
from bot.decision import decide
from bot.features import build_state
from bot.jev import JevClient
from bot.kalshi import KalshiClient


def main() -> None:
    config = load_config()
    client = KalshiClient(
        config.api_key_id, config.private_key_path, config.base_url
    )
    market = client.get_current_market(config.series_ticker)
    orderbook = client.get_orderbook(market["ticker"])

    brti_points = []
    if client.can_auth:
        try:
            brti_points = client.get_brti_values(config.brti_index)
        except Exception as exc:
            print(f"warning: BRTI unavailable: {exc}")
    else:
        print(
            "warning: set KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH to fetch BRTI"
        )

    state = build_state(market, orderbook, brti_points)
    print(json.dumps(state, indent=2))

    jev = JevClient(
        config.typesafe_api_key, config.typesafe_base_url, config.typesafe_model
    )
    if not jev.can_call:
        print("warning: set TYPESAFE_API_KEY to call Jev")
        return

    try:
        prediction = jev.predict_up(state)
    except Exception as exc:
        print(f"warning: Jev unavailable: {exc}")
        return

    decision = decide(state, prediction["probability_up"], config)
    print(json.dumps({"prediction": prediction, "decision": decision}, indent=2))


if __name__ == "__main__":
    main()
