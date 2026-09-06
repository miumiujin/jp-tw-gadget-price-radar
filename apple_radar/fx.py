from __future__ import annotations
from datetime import datetime, timezone
import requests


FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rate/JPY/TWD"


def fetch_jpy_twd(timeout: int = 15) -> tuple[float, datetime]:
    """Return TWD value of 1 JPY and observation time."""
    response = requests.get(
        FRANKFURTER_URL,
        timeout=timeout,
        headers={"User-Agent": "JP-TW-Apple-Price-Radar/0.1"},
    )
    response.raise_for_status()
    payload = response.json()

    # v2/rate payload is expected to include a numeric rate.
    if isinstance(payload, dict):
        for key in ("rate", "value"):
            if key in payload:
                return float(payload[key]), datetime.now(timezone.utc)

    # Defensive fallback for array-style API responses.
    if isinstance(payload, list) and payload:
        item = payload[0]
        for key in ("rate", "value"):
            if key in item:
                return float(item[key]), datetime.now(timezone.utc)

    raise ValueError(f"Unexpected FX response: {payload!r}")
