from __future__ import annotations

from .config import load_products
from .db import DEFAULT_DB, init_db, save_fx, save_observation
from .fx import fetch_jpy_twd
from .sources.apple_official import official_new_observations
from .sources.iosys import fetch_iosys_used
from .sources.janpara import fetch_janpara_used
from .sources.sofmap import fetch_sofmap_used
from .sources.us3c import fetch_us3c_market


JAPAN_USED_SOURCES = (
    ("Sofmap", fetch_sofmap_used),
    ("Janpara", fetch_janpara_used),
    ("IOSYS", fetch_iosys_used),
)


def run_ingestion(db_path=DEFAULT_DB):
    init_db(db_path)
    products = load_products()

    fx_rate, fx_time = fetch_jpy_twd()
    save_fx(fx_rate, fx_time, db_path)

    inserted = 0
    errors = []
    misses = []

    for product in products:
        # Stable official new-price baseline.
        try:
            for obs in official_new_observations(product, fx_rate):
                save_observation(obs, db_path)
                inserted += 1
        except Exception as exc:
            errors.append((product["id"], "Apple Official", str(exc)))

        # Japan used/public-retail market.
        for source_name, fn in JAPAN_USED_SOURCES:
            try:
                observations = fn(product, fx_rate)
                if not observations:
                    misses.append((product["id"], source_name))
                    continue
                for obs in observations:
                    save_observation(obs, db_path)
                    inserted += 1
            except Exception as exc:
                errors.append((product["id"], source_name, str(exc)))

        # Taiwan second-hand market reference.
        try:
            observations = fetch_us3c_market(product)
            if not observations:
                misses.append((product["id"], "US3C"))
            for obs in observations:
                save_observation(obs, db_path)
                inserted += 1
        except Exception as exc:
            errors.append((product["id"], "US3C", str(exc)))

    return {
        "products": len(products),
        "observations": inserted,
        "fx_rate": fx_rate,
        "misses": misses,
        "errors": errors,
    }
