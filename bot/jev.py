from __future__ import annotations

from typing import Any

import requests

QUESTION_ID = "up"
QUESTION = {
    "type": "noul",
    "instructions": (
        "Will the 60-second BRTI average at the close of the current "
        "15-minute window be greater than or equal to the target price?"
    ),
    "criteria": {
        "true": (
            "The 60-second BRTI average at close is greater than or equal "
            "to the target price."
        ),
        "false": (
            "The 60-second BRTI average at close is below the target price."
        ),
    },
}


class JevClient:
    def __init__(
        self, api_key: str | None, base_url: str, model: str
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def can_call(self) -> bool:
        return bool(self.api_key)

    def predict_up(self, state: dict[str, Any]) -> dict[str, Any]:
        if not self.can_call:
            raise RuntimeError("TYPESAFE_API_KEY is not configured")
        response = requests.post(
            f"{self.base_url}/v1/systemone",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "state": state,
                "questions": {QUESTION_ID: QUESTION},
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        answer = (data.get("answers") or {}).get(QUESTION_ID) or {}
        probability = answer.get("noul")
        if probability is None:
            raise RuntimeError(f"Unexpected Jev response: {data}")
        return {
            "probability_up": float(probability),
            "model": data.get("model"),
            "usage": data.get("usage"),
        }
