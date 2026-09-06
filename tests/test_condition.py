from datetime import datetime, timezone
from apple_radar.models import PriceObservation


def test_condition_field_defaults():
    obs = PriceObservation(
        product_id="x",
        source="s",
        source_country="JP",
        raw_title="x",
        price=1,
        currency="JPY",
        price_twd=0.2,
        observed_at=datetime.now(timezone.utc),
        url="https://example.com",
    )
    assert obs.condition == "unknown"
