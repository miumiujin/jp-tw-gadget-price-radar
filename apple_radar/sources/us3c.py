from __future__ import annotations
from datetime import datetime, timezone
import re

import requests
from bs4 import BeautifulSoup

from ..models import PriceObservation


APPLE_MARKET_URL = "https://www.us3c.com.tw/purchase/35/apple-second-hand"
MONEY_RE = re.compile(r"市場均價\s*\$?\s*([\d,]+)")


def _clean_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in soup.get_text("\n", strip=True).splitlines()
        if line.strip()
    ]


def _score_line(line: str, terms: list[str]) -> int:
    lower = line.lower()
    return sum(term.lower() in lower for term in terms)


def fetch_us3c_market(product: dict, timeout: int = 20):
    response = requests.get(
        APPLE_MARKET_URL,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 ApplePriceRadar/0.1"},
    )
    response.raise_for_status()
    lines = _clean_lines(response.text)

    terms = product.get("us3c_terms", [])
    candidates = []

    # On the US3C Apple market page, a product title is followed nearby by
    # official/buyback information and a "市場均價" reference.
    for i, line in enumerate(lines):
        match_score = _score_line(line, terms)
        if match_score < max(2, len(terms) - 1):
            continue

        nearby = " ".join(lines[i : i + 14])
        m = MONEY_RE.search(nearby)
        if m:
            candidates.append((match_score, line, int(m.group(1).replace(",", ""))))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, title, market_avg = candidates[0]

    return [
        PriceObservation(
            product_id=product["id"],
            source="US3C Market Avg",
            source_country="TW",
            raw_title=title,
            price=float(market_avg),
            currency="TWD",
            price_twd=float(market_avg),
            observed_at=datetime.now(timezone.utc),
            url=APPLE_MARKET_URL,
            note="US3C public market-average benchmark; verify exact model before purchase",
            condition="market_reference",
        )
    ]
