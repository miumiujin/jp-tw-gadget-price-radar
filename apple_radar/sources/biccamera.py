from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup, Tag

from ..http_client import PublicPageFetchError, fetch_html_fast
from ..models import PriceObservation


SEARCH_URL = "https://www.biccamera.com/bc/category/?q={query}"

USED_PRICE_RE = re.compile(
    r"中古品\s*(?:\d+\s*点)?\s*([\d,]+)\s*円(?:（税込）)?\s*(?:～|〜)?",
    re.IGNORECASE,
)

ITEM_PATH_RE = re.compile(r"/bc/item/\d+/?")

DEFAULT_FORBIDDEN = (
    "ケース", "カバー", "フィルム", "保護フィルム", "ガラス",
    "スタンド", "アダプタ", "ケーブル", "アクセサリー", "キーボードケース",
)


@dataclass(slots=True)
class BicCandidate:
    title: str
    item_url: str
    used_price_jpy: int
    match_score: int
    card_text: str
    source_page: str = ""


@dataclass(slots=True)
class BicFetchReport:
    pages_tried: list[str]
    pages_loaded: list[str]
    page_errors: list[str]
    candidates: list[BicCandidate]


def _norm(text: str) -> str:
    text = str(text or "").replace("　", " ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text.replace("wi‐fi", "wi-fi").replace("wifi", "wi-fi")


def _matches_required_groups(title: str, groups: list[list[str]]) -> tuple[bool, int]:
    normalized = _norm(title)
    score = 0

    for alternatives in groups:
        if not any(_norm(token) in normalized for token in alternatives):
            return False, score
        score += 1

    return True, score


def _contains_forbidden(title: str, forbidden: list[str]) -> bool:
    normalized = _norm(title)
    return any(_norm(token) in normalized for token in forbidden)


def _best_card_for_anchor(anchor: Tag) -> Tag | None:
    node: Tag | None = anchor
    best: Tag | None = None

    for _ in range(10):
        if node is None:
            break

        text = node.get_text(" ", strip=True)
        if USED_PRICE_RE.search(text):
            best = node
            if 80 <= len(text) <= 5000:
                return best

        parent = node.parent
        node = parent if isinstance(parent, Tag) else None

    return best


def parse_bic_search_html(
    html: str,
    product: dict,
    source_page: str = "",
) -> list[BicCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    required_groups = product.get("bic_required_groups", [])
    forbidden = list(DEFAULT_FORBIDDEN) + list(product.get("bic_forbidden_tokens", []))
    candidates_by_url: dict[str, BicCandidate] = {}

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not ITEM_PATH_RE.search(href):
            continue

        title = anchor.get_text(" ", strip=True)
        if not title:
            image = anchor.find("img", alt=True)
            title = image.get("alt", "").strip() if image else ""

        if not title or _contains_forbidden(title, forbidden):
            continue

        matched, score = _matches_required_groups(title, required_groups)
        if required_groups and not matched:
            continue

        card = _best_card_for_anchor(anchor)
        if card is None:
            continue

        card_text = card.get_text(" ", strip=True)
        prices = [int(v.replace(",", "")) for v in USED_PRICE_RE.findall(card_text)]
        if not prices:
            continue

        item_url = urljoin("https://www.biccamera.com", href)
        candidate = BicCandidate(
            title=title,
            item_url=item_url,
            used_price_jpy=min(prices),
            match_score=score,
            card_text=card_text[:1200],
            source_page=source_page,
        )

        old = candidates_by_url.get(item_url)
        if old is None or (
            candidate.match_score, -candidate.used_price_jpy
        ) > (
            old.match_score, -old.used_price_jpy
        ):
            candidates_by_url[item_url] = candidate

    return sorted(
        candidates_by_url.values(),
        key=lambda c: (-c.match_score, c.used_price_jpy, c.title),
    )


def candidate_pages(product: dict) -> list[str]:
    urls = list(product.get("bic_urls", []))
    if urls:
        return urls

    query = quote_plus(product.get("bic_query", product["id"]))
    return [SEARCH_URL.format(query=query)]


def fetch_biccamera_candidates(
    product: dict,
    timeout: int = 25,
) -> BicFetchReport:
    """
    Fast-fail policy:

    - Try the primary, most specific Bic page once.
    - If the primary page TIMES OUT / fails to load, stop Bic for this product.
      Do not multiply a network problem across fallback URLs.
    - Only try a fallback page if the primary loaded successfully but had no
      exact-spec product candidate.
    - Return immediately when exact candidates are found.
    """
    pages = candidate_pages(product)
    report = BicFetchReport(
        pages_tried=[],
        pages_loaded=[],
        page_errors=[],
        candidates=[],
    )

    for index, url in enumerate(pages):
        report.pages_tried.append(url)

        try:
            html = fetch_html_fast(url, timeout=timeout)
        except PublicPageFetchError as exc:
            report.page_errors.append(f"{url} -> {exc}")

            # Primary networking failure: fail fast.
            if index == 0:
                return report

            continue

        report.pages_loaded.append(url)
        candidates = parse_bic_search_html(html, product, source_page=url)

        if candidates:
            report.candidates = candidates
            return report

        # Page loaded fine but matching failed: now and only now try fallback.
        continue

    return report


def fetch_biccamera_used(product: dict, fx_rate: float, timeout: int = 25):
    report = fetch_biccamera_candidates(product, timeout=timeout)

    if not report.candidates:
        return []

    best_score = max(c.match_score for c in report.candidates)
    equally_matched = [
        c for c in report.candidates
        if c.match_score == best_score
    ]
    best = min(equally_matched, key=lambda c: c.used_price_jpy)

    return [
        PriceObservation(
            product_id=product["id"],
            source="Bic Camera",
            source_country="JP",
            raw_title=best.title,
            price=float(best.used_price_jpy),
            currency="JPY",
            price_twd=round(best.used_price_jpy * fx_rate, 0),
            observed_at=datetime.now(timezone.utc),
            url=best.item_url,
            note=(
                f"Exact-spec Bic Camera product-card match; "
                f"{len(report.candidates)} matching used listing(s). "
                f"Source page: {best.source_page}"
            ),
        )
    ]
