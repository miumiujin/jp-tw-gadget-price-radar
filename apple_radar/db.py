from __future__ import annotations
from pathlib import Path
import sqlite3

from .models import PriceObservation


DEFAULT_DB = Path("data/apple_prices.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS price_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_country TEXT NOT NULL,
    raw_title TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    price_twd REAL NOT NULL,
    observed_at TEXT NOT NULL,
    observed_date TEXT NOT NULL,
    url TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    condition TEXT NOT NULL DEFAULT 'unknown',
    UNIQUE(product_id, source, observed_date)
);

CREATE TABLE IF NOT EXISTS fx_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    rate REAL NOT NULL,
    observed_at TEXT NOT NULL,
    observed_date TEXT NOT NULL,
    UNIQUE(pair, observed_date)
);
"""


def connect(db_path=DEFAULT_DB):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_condition_column(conn: sqlite3.Connection):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(price_observations)").fetchall()
    }
    if "condition" not in columns:
        conn.execute(
            "ALTER TABLE price_observations "
            "ADD COLUMN condition TEXT NOT NULL DEFAULT 'unknown'"
        )


def init_db(db_path=DEFAULT_DB):
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _ensure_condition_column(conn)


def save_fx(rate: float, observed_at, db_path=DEFAULT_DB):
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO fx_rates(pair, rate, observed_at, observed_date)
            VALUES (?, ?, ?, ?)
            """,
            ("JPY/TWD", rate, observed_at.isoformat(), observed_at.date().isoformat()),
        )


def save_observation(obs: PriceObservation, db_path=DEFAULT_DB):
    with connect(db_path) as conn:
        _ensure_condition_column(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO price_observations(
                product_id, source, source_country, raw_title,
                price, currency, price_twd, observed_at,
                observed_date, url, note, condition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs.product_id,
                obs.source,
                obs.source_country,
                obs.raw_title,
                obs.price,
                obs.currency,
                obs.price_twd,
                obs.observed_at.isoformat(),
                obs.observed_at.date().isoformat(),
                obs.url,
                obs.note,
                obs.condition,
            ),
        )
