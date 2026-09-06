from __future__ import annotations
from datetime import datetime, timezone

from ..models import PriceObservation


def build_product_title(product: dict) -> str:
    if product.get("display_name"):
        return product["display_name"]

    parts = [product.get("family")]
    if product.get("variant"):
        parts.append(product["variant"])
    elif product.get("chip"):
        parts.append(str(product.get("chip")))

    detail_bits = []
    if product.get("screen"):
        detail_bits.append(f'{product.get("screen")}"')
    if product.get("ram_gb"):
        detail_bits.append(f'{product.get("ram_gb")}GB')
    if product.get("storage_gb"):
        detail_bits.append(f'{product.get("storage_gb")}GB')
    if product.get("connectivity"):
        detail_bits.append(str(product.get("connectivity")))

    if detail_bits:
        parts.append(" / ".join(detail_bits))

    return " ".join(str(x).strip() for x in parts if x).strip()


def official_new_observations(product: dict, fx_rate: float):
    """
    Keep infrequently changing official list prices in config and convert JP price daily.
    Supports Apple / Sony / Nintendo / other brands through configurable source names.
    """
    official = product.get("official_new")
    if not official:
        return []

    now = datetime.now(timezone.utc)
    title = build_product_title(product)
    note = official.get("note") or f'Official new MSRP; verified {official.get("verified_at","")}'

    rows = []

    jp = official.get("jp")
    if jp:
        price_jpy = float(jp["price"])
        rows.append(
            PriceObservation(
                product_id=product["id"],
                source=jp.get("source", official.get("jp_source", "Official JP")),
                source_country="JP",
                raw_title=title,
                price=price_jpy,
                currency="JPY",
                price_twd=round(price_jpy * fx_rate, 0),
                observed_at=now,
                url=jp["url"],
                note=note,
                condition="new",
            )
        )

    tw = official.get("tw")
    if tw:
        price_twd = float(tw["price"])
        rows.append(
            PriceObservation(
                product_id=product["id"],
                source=tw.get("source", official.get("tw_source", "Official TW")),
                source_country="TW",
                raw_title=title,
                price=price_twd,
                currency="TWD",
                price_twd=price_twd,
                observed_at=now,
                url=tw["url"],
                note=note,
                condition="new",
            )
        )

    return rows
