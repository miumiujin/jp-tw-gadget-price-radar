from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup, Tag

from ..http_client import fetch_html_fast
from ..models import PriceObservation
from .common import matches_product


BASE = "https://www.sofmap.com"
SEARCH_URL = (
    "https://www.sofmap.com/search_result.aspx"
    "?keyword={query}&product_type=USED&stk_flg=1"
)

PRODUCT_RE = re.compile(r"product_detail\.aspx\?sku=\d+", re.I)
PRICE_RE = re.compile(r"¥\s*([\d,]+)\s*\(税込\)")
RANK_RE = re.compile(r"(?:中古商品ランク|ランク)\s*([SABCDE])")


@dataclass(slots=True)
class SofmapCandidate:
    title: str
    price_jpy: int
    url: str
    rank: str
    score: int


def _find_card(anchor: Tag) -> Tag | None:
    node: Tag | None = anchor
    best = None
    for _ in range(9):
        if node is None:
            break
        text = node.get_text(" ", strip=True)
        if PRICE_RE.search(text):
            best = node
            if len(text) >= 80:
                return best
        parent = node.parent
        node = parent if isinstance(parent, Tag) else None
    return best


def parse_sofmap_html(html: str, product: dict) -> list[SofmapCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    results: dict[str, SofmapCandidate] = {}

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not PRODUCT_RE.search(href):
            continue

        title = a.get_text(" ", strip=True)
        if not title:
            img = a.find("img", alt=True)
            title = img.get("alt", "").strip() if img else ""
        if not title:
            continue

        matched, score = matches_product(title, product)
        if not matched:
            continue

        card = _find_card(a)
        if card is None:
            continue

        card_text = card.get_text(" ", strip=True)
        prices = [int(v.replace(",", "")) for v in PRICE_RE.findall(card_text)]
        if not prices:
            continue

        rank_m = RANK_RE.search(card_text)
        rank = rank_m.group(1) if rank_m else ""

        url = urljoin(BASE, href)
        candidate = SofmapCandidate(
            title=title,
            price_jpy=min(prices),
            url=url,
            rank=rank,
            score=score,
        )
        old = results.get(url)
        if old is None or candidate.price_jpy < old.price_jpy:
            results[url] = candidate

    return sorted(results.values(), key=lambda x: (x.price_jpy, -x.score))


def fetch_sofmap_used(product: dict, fx_rate: float, timeout: int = 25):
    url = SEARCH_URL.format(query=quote_plus(product["sofmap_query"]))
    html = fetch_html_fast(url, timeout=timeout)
    candidates = parse_sofmap_html(html, product)
    if not candidates:
        return []

    best = candidates[0]
    return [
        PriceObservation(
            product_id=product["id"],
            source="Sofmap",
            source_country="JP",
            raw_title=best.title,
            price=float(best.price_jpy),
            currency="JPY",
            price_twd=round(best.price_jpy * fx_rate, 0),
            observed_at=datetime.now(timezone.utc),
            url=best.url,
            note=f"Sofmap used listing; rank={best.rank or 'unknown'}",
            condition="used",
        )
    ]
