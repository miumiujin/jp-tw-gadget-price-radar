from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PriceObservation:
    product_id: str
    source: str
    source_country: str
    raw_title: str
    price: float
    currency: str
    price_twd: float
    observed_at: datetime
    url: str
    note: str = ""
    condition: str = "unknown"  # new | unused | used | market_reference
