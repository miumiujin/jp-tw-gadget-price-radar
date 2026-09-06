from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..http_client import fetch_html_fast
from ..models import PriceObservation
from .common import matches_product


SEARCH_URL = "https://iosys.co.jp/items?q={query}"

PRICE_RE = re.compile(r"([\d,]+)円\s*\(税込\)")
RANK_RE = re.compile(r"(中古[A-C]ランク|未使用品)")
STOCK_RE = re.compile(r"在庫数[:：]\s*(\d+)")


def parse_iosys_html(html: str, product: dict):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines() if x.strip()]
    candidates = []

    for i, line in enumerate(lines):
        matched, score = matches_product(line, product)
        if not matched:
            continue

        nearby = " ".join(lines[i:i+10])
        price_m = PRICE_RE.search(nearby)
        if not price_m:
            continue

        rank_m = RANK_RE.search(nearby)
        stock_m = STOCK_RE.search(nearby)
        rank = rank_m.group(1) if rank_m else ""
        stock = int(stock_m.group(1)) if stock_m else None

        # Do not use out-of-stock records when stock is explicitly zero.
        if stock == 0:
            continue

        candidates.append({
            "title": line,
            "price_jpy": int(price_m.group(1).replace(",", "")),
            "rank": rank,
            "stock": stock,
            "score": score,
        })

    unique = {}
    for c in candidates:
        key = (c["title"], c["price_jpy"], c["rank"])
        unique[key] = c

    return sorted(unique.values(), key=lambda x: (x["price_jpy"], -x["score"]))


def fetch_iosys_used(product: dict, fx_rate: float, timeout: int = 25):
    url = SEARCH_URL.format(query=quote_plus(product["iosys_query"]))
    html = fetch_html_fast(url, timeout=timeout)
    rows = parse_iosys_html(html, product)
    if not rows:
        return []

    best = rows[0]
    note_bits = []
    if best["rank"]:
        note_bits.append(best["rank"])
    if best["stock"] is not None:
        note_bits.append(f"stock={best['stock']}")

    return [
        PriceObservation(
            product_id=product["id"],
            source="IOSYS",
            source_country="JP",
            raw_title=best["title"],
            price=float(best["price_jpy"]),
            currency="JPY",
            price_twd=round(best["price_jpy"] * fx_rate, 0),
            observed_at=datetime.now(timezone.utc),
            url=url,
            note="IOSYS public listing; " + ", ".join(note_bits),
            condition=("unused" if "未使用" in (best["rank"] or "") else "used"),
        )
    ]
