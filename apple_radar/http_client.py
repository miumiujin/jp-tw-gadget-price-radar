from __future__ import annotations

import requests

try:
    from curl_cffi import requests as curl_requests
except Exception:  # pragma: no cover
    curl_requests = None


DEFAULT_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.7,en;q=0.5",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.google.co.jp/",
    "Upgrade-Insecure-Requests": "1",
}


class PublicPageFetchError(RuntimeError):
    pass


def fetch_html_fast(
    url: str,
    *,
    timeout: int = 25,
) -> str:
    """
    Fast-fail public-page fetcher.

    Strategy:
    1. Prefer curl_cffi with Chrome TLS/browser impersonation.
    2. Do exactly ONE network attempt.
    3. If curl_cffi is unavailable, use requests once.
    4. Never stack multiple retries that can make one source hang for minutes.

    The caller decides whether/when to try a fallback URL.
    """
    if curl_requests is not None:
        try:
            response = curl_requests.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                impersonate="chrome124",
                allow_redirects=True,
            )
        except Exception as exc:
            raise PublicPageFetchError(
                f"curl_cffi {type(exc).__name__}: {exc}"
            ) from exc

        if not (200 <= response.status_code < 400):
            raise PublicPageFetchError(
                f"HTTP {response.status_code} from public page"
            )

        if not response.text:
            raise PublicPageFetchError("Empty response body")

        return response.text

    headers = dict(DEFAULT_HEADERS)
    headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=(8, timeout),
            allow_redirects=True,
        )
    except Exception as exc:
        raise PublicPageFetchError(
            f"requests {type(exc).__name__}: {exc}"
        ) from exc

    if not (200 <= response.status_code < 400):
        raise PublicPageFetchError(
            f"HTTP {response.status_code} from public page"
        )

    if not response.text:
        raise PublicPageFetchError("Empty response body")

    return response.text
