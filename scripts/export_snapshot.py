from pathlib import Path
import json
import sqlite3

DB = Path("data/apple_prices.db")
OUT = Path("data/latest_snapshot.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(DB) as conn:
    conn.row_factory = sqlite3.Row
    fx = conn.execute(
        "SELECT * FROM fx_rates ORDER BY observed_at DESC LIMIT 1"
    ).fetchone()
    rows = conn.execute(
        """
        SELECT p.*
        FROM price_observations p
        JOIN (
          SELECT product_id, source, MAX(observed_at) AS mx
          FROM price_observations
          GROUP BY product_id, source
        ) q
        ON p.product_id=q.product_id AND p.source=q.source AND p.observed_at=q.mx
        ORDER BY p.product_id, p.source
        """
    ).fetchall()

payload = {
    "fx": dict(fx) if fx else None,
    "prices": [dict(row) for row in rows],
}

OUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"Wrote {OUT}")
