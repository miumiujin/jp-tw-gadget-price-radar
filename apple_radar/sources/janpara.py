from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..http_client import fetch_html_fast
from ..models import PriceObservation
from .common import matches_product


SEARCH_URL = (
    "https://www.janpara.co.jp/sale/search/result/"
    "?KEYWORDS={query}&OUTCLSCODE=&viewmodechange=2"
)

PRICE_RE = re.compile(r"中古\s*¥\s*([\d,]+)\s*[～〜]?")
STOCK_RE = re.compile(r"(\d+)個の在庫")


def parse_janpara_html(html: str, product: dict):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines() if x.strip()]
    candidates = []

    # Janpara result pages expose a product title followed by stock and "中古 ¥xx,xxx～".
    for i, line in enumerate(lines):
        matched, score = matches_product(line, product)
        if not matched:
            continue

        nearby = " ".join(lines[i:i+7])
        price_m = PRICE_RE.search(nearby)
        if not price_m:
            continue

        stock_m = STOCK_RE.search(nearby)
        stock = int(stock_m.group(1)) if stock_m else None

        candidates.append({
            "title": line,
            "price_jpy": int(price_m.group(1).replace(",", "")),
            "stock": stock,
            "score": score,
        })

    # De-duplicate equivalent title/price rows.
    unique = {}
    for c in candidates:
        key = (c["title"], c["price_jpy"])
        unique[key] = c

    return sorted(unique.values(), key=lambda x: (x["price_jpy"], -x["score"]))


def fetch_janpara_used(product: dict, fx_rate: float, timeout: int = 25):
    url = SEARCH_URL.format(query=quote_plus(product["janpara_query"]))
    html = fetch_html_fast(url, timeout=timeout)
    rows = parse_janpara_html(html, product)
    if not rows:
        return []

    best = rows[0]
    stock_note = f"stock={best['stock']}" if best["stock"] is not None else "stock=unknown"

    return [
        PriceObservation(
            product_id=product["id"],
            source="Janpara",
            source_country="JP",
            raw_title=best["title"],
            price=float(best["price_jpy"]),
            currency="JPY",
            price_twd=round(best["price_jpy"] * fx_rate, 0),
            observed_at=datetime.now(timezone.utc),
            url=url,
            note=f"Janpara public search result; {stock_note}",
            condition="used",
        )
    ]
