from apple_radar.sources.apple_official import official_new_observations, build_product_title


def test_generic_official_source_names():
    product = {
        "id": "ps5-slim-disc",
        "family": "PlayStation 5",
        "display_name": "PlayStation 5 Slim",
        "official_new": {
            "verified_at": "2026-09-06",
            "jp": {
                "price": 79980,
                "url": "https://example.com/jp",
                "source": "Sony Store JP",
            },
            "tw": {
                "price": 19989,
                "url": "https://example.com/tw",
                "source": "Sony Store TW",
            },
        },
    }

    rows = official_new_observations(product, 0.2)
    assert rows[0].source == "Sony Store JP"
    assert rows[1].source == "Sony Store TW"
    assert rows[0].price_twd == round(79980 * 0.2, 0)


def test_build_product_title_prefers_display_name():
    product = {
        "id": "switch-2",
        "family": "Nintendo Switch 2",
        "display_name": "Nintendo Switch 2",
        "variant": "Standard Console",
    }
    assert build_product_title(product) == "Nintendo Switch 2"
