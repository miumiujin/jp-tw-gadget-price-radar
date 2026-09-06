from __future__ import annotations
import re


def normalize(text: str) -> str:
    text = str(text or "").replace("　", " ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return (
        text.replace("wi‐fi", "wi-fi")
        .replace("wifi", "wi-fi")
        .replace("／", "/")
        .replace("：", ":")
    )


def matches_product(text: str, product: dict) -> tuple[bool, int]:
    normalized = normalize(text)

    for forbidden in product.get("forbidden_tokens", []):
        if normalize(forbidden) in normalized:
            return False, 0

    score = 0
    for alternatives in product.get("required_groups", []):
        if not any(normalize(token) in normalized for token in alternatives):
            return False, score
        score += 1

    return True, score
