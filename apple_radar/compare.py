from __future__ import annotations


def savings(japan_twd: float | None, taiwan_twd: float | None):
    if not japan_twd or not taiwan_twd:
        return None

    amount = taiwan_twd - japan_twd
    pct = amount / taiwan_twd * 100 if taiwan_twd else 0

    if pct >= 20:
        verdict = "🔥 日本買很有優勢"
    elif pct >= 10:
        verdict = "🟢 日本買較划算"
    elif pct >= 3:
        verdict = "🟡 小幅便宜"
    elif pct > -3:
        verdict = "⚪ 價格接近"
    else:
        verdict = "🇹🇼 台灣買較划算"

    return {
        "amount": round(amount),
        "pct": round(pct, 1),
        "verdict": verdict,
    }
