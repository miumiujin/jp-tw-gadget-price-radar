# JP–TW Gadget Price Radar 🇯🇵⇄🇹🇼

A tourist-first public price comparison dashboard for Japan vs Taiwan.

Now it covers:
- Apple laptops / tablets / audio
- Nintendo Switch 2
- PlayStation 5
- Japanese public used-market sources: Sofmap / Janpara / IOSYS
- Official new-price references for Japan and Taiwan when available

## What's new in v0.4.0

- Added more product categories: **gaming** and **audio**
- Added example tracked products for:
  - Nintendo Switch 2
  - PlayStation 5 Slim (Disc)
  - AirPods 4 ANC
- UI refresh: a more fashion / editorial dashboard style
- Official price ingestion is now **generic**, not Apple-only
- Existing CLI stays the same:
  - `apple-radar ingest`
  - `apple-radar source-debug <source> <product_id>`

## Quick start

```bash
conda create -n apple-price-radar python=3.11 -y
conda activate apple-price-radar
pip install -e ".[dev]"
```

Fetch current data:

```bash
apple-radar ingest
```

Run dashboard:

```bash
streamlit run app.py
```

## Example debug

```bash
apple-radar source-debug janpara macbook-air-m2-13-8-256
apple-radar source-debug sofmap airpods-4-anc
apple-radar source-debug iosys nintendo-switch-2
```

## Notes

- Public pages can change markup anytime.
- Some non-Apple products may not have Taiwan used-market references yet.
- Official prices are stored in `config/products.yaml` and can be updated manually.
- Always verify tax-free eligibility, warranty, language region, and exact SKU before buying.
