from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st
import yaml

from apple_radar.compare import savings
from apple_radar.db import DEFAULT_DB
from apple_radar.pipeline import run_ingestion

DB = DEFAULT_DB
JAPAN_USED = ["Sofmap", "Janpara", "IOSYS"]
SEGMENT_ICONS = {"Laptop": "💻", "Tablet": "📱", "Audio": "🎧", "Gaming": "🎮"}
SEGMENT_JP = {"Laptop": "ノートPC", "Tablet": "タブレット", "Audio": "オーディオ", "Gaming": "ゲーム"}


def product_title(product: dict) -> str:
    return product.get("display_name") or product.get("family") or product["id"]


def product_subtitle(product: dict) -> str:
    if product.get("spec_override"):
        return product["spec_override"]
    bits = []
    if product.get("variant"):
        bits.append(str(product["variant"]))
    if product.get("chip"):
        bits.append(str(product["chip"]))
    if product.get("screen"):
        bits.append(f'{product.get("screen")}"')
    if product.get("ram_gb"):
        bits.append(f'{product.get("ram_gb")}GB RAM')
    if product.get("storage_gb"):
        bits.append(f'{product.get("storage_gb")}GB')
    if product.get("connectivity"):
        bits.append(str(product.get("connectivity")))
    return " · ".join(bits)


def safe_int(value):
    return int(float(value)) if value is not None else None


def deal_class(pct):
    if pct is None:
        return "neutral"
    if pct >= 10:
        return "hot"
    if pct >= 3:
        return "good"
    return "neutral"


def compute_top_deals(products, prices):
    deals = []
    for product in products:
        rows = prices[prices["product_id"] == product["id"]].copy()
        jp_new = rows[(rows["condition"] == "new") & (rows["source_country"] == "JP")]
        tw_new = rows[(rows["condition"] == "new") & (rows["source_country"] == "TW")]
        if not jp_new.empty and not tw_new.empty:
            d = savings(float(jp_new.iloc[0]["price_twd"]), float(tw_new.iloc[0]["price_twd"]))
            if d:
                deals.append({
                    "product": product,
                    "mode": "新品",
                    "pct": d["pct"],
                    "verdict": d["verdict"],
                    "japan_twd": safe_int(jp_new.iloc[0]["price_twd"]),
                    "taiwan_twd": safe_int(tw_new.iloc[0]["price_twd"]),
                })

        used_jp = rows[
            (rows["source_country"] == "JP")
            & (rows["source"].isin(JAPAN_USED))
            & (rows["condition"].isin(["used", "unused", "unknown"]))
        ]
        tw_ref = rows[rows["source"] == "US3C Market Avg"]
        if not used_jp.empty and not tw_ref.empty:
            best = used_jp.sort_values("price_twd").iloc[0]
            d = savings(float(best["price_twd"]), float(tw_ref.iloc[0]["price_twd"]))
            if d:
                deals.append({
                    "product": product,
                    "mode": "中古",
                    "pct": d["pct"],
                    "verdict": d["verdict"],
                    "japan_twd": safe_int(best["price_twd"]),
                    "taiwan_twd": safe_int(tw_ref.iloc[0]["price_twd"]),
                })
    return sorted(deals, key=lambda x: x["pct"], reverse=True)


st.set_page_config(page_title="JP–TW Gadget Price Radar", page_icon="🗼", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    :root { --ink:#f8fafc; --muted:#94a3b8; --line:rgba(255,255,255,.08); }
    .stApp {
      background:
        radial-gradient(circle at 9% -5%, rgba(99,102,241,.30), transparent 30%),
        radial-gradient(circle at 91% 3%, rgba(244,63,94,.20), transparent 28%),
        radial-gradient(circle at 78% 76%, rgba(14,165,233,.11), transparent 25%),
        linear-gradient(180deg,#030712 0%,#08111f 42%,#040914 100%);
      color:var(--ink);
    }
    .main .block-container {max-width:1400px;padding-top:1.1rem;padding-bottom:4rem;}
    [data-testid="stSidebar"] {background:linear-gradient(180deg,rgba(5,15,31,.99),rgba(4,10,22,.99));border-right:1px solid var(--line);}
    @keyframes floatGlow {0%{transform:translate3d(0,0,0) scale(1);opacity:.55}50%{transform:translate3d(-16px,14px,0) scale(1.08);opacity:.8}100%{transform:translate3d(0,0,0) scale(1);opacity:.55}}
    @keyframes fadeUp {from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
    @keyframes shine {0%{transform:translateX(-130%)}100%{transform:translateX(160%)}}
    .hero {position:relative;overflow:hidden;background:linear-gradient(135deg,rgba(12,27,58,.96),rgba(18,24,51,.88));border:1px solid rgba(255,255,255,.09);border-radius:34px;padding:38px 40px;margin-bottom:22px;box-shadow:0 30px 80px rgba(0,0,0,.38);animation:fadeUp .55s ease-out both;}
    .hero:before {content:"";position:absolute;right:-70px;top:-90px;width:330px;height:330px;border-radius:50%;background:radial-gradient(circle,rgba(244,63,94,.25),transparent 65%);animation:floatGlow 7s ease-in-out infinite;}
    .hero:after {content:"東京 ⇄ 台北";position:absolute;right:35px;bottom:22px;font-size:4.2rem;font-weight:900;letter-spacing:.05em;color:rgba(255,255,255,.025);pointer-events:none;}
    .eyebrow {color:#fda4af;font-size:.77rem;font-weight:900;letter-spacing:.18em;}
    .hero h1 {font-size:3.35rem;font-weight:950;margin:.35rem 0 .7rem;line-height:1.03;}
    .hero p {color:#cbd5e1;max-width:980px;line-height:1.85;font-size:1.01rem;}
    .chip-row {display:flex;gap:10px;flex-wrap:wrap;margin-top:15px;}
    .chip {display:inline-flex;align-items:center;gap:7px;padding:8px 14px;border-radius:999px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.05);color:#dbeafe;font-size:.84rem;font-weight:800;backdrop-filter:blur(8px);}
    .stat-card {border-radius:25px;padding:18px 20px;min-height:118px;background:linear-gradient(180deg,rgba(12,23,43,.94),rgba(7,14,28,.90));border:1px solid var(--line);box-shadow:0 14px 32px rgba(0,0,0,.22);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;}
    .stat-card:hover {transform:translateY(-3px);border-color:rgba(125,211,252,.18);box-shadow:0 18px 42px rgba(0,0,0,.28);}
    .stat-label {color:#94a3b8;font-size:.76rem;letter-spacing:.13em;font-weight:900;}
    .stat-value {font-size:2.35rem;font-weight:950;margin-top:8px;}
    .deal-ribbon {font-size:.75rem;font-weight:900;letter-spacing:.08em;color:#fde68a;}
    .deal-card {position:relative;overflow:hidden;border-radius:24px;padding:18px 20px;background:linear-gradient(135deg,rgba(16,29,56,.96),rgba(13,19,39,.92));border:1px solid rgba(255,255,255,.09);min-height:176px;box-shadow:0 15px 34px rgba(0,0,0,.23);transition:all .2s ease;}
    .deal-card:hover {transform:translateY(-5px) scale(1.005);border-color:rgba(251,113,133,.28);}
    .deal-card:before {content:"";position:absolute;top:0;left:0;width:45%;height:100%;background:linear-gradient(110deg,transparent,rgba(255,255,255,.035),transparent);transform:translateX(-130%);animation:shine 5.5s infinite;}
    .deal-name {font-size:1.18rem;font-weight:900;margin-top:7px;}
    .deal-pct {font-size:2.15rem;font-weight:950;margin-top:12px;}
    .deal-meta {font-size:.82rem;color:#94a3b8;line-height:1.55;}
    .hot .deal-pct {color:#fda4af}.good .deal-pct {color:#86efac}.neutral .deal-pct {color:#bfdbfe}
    div[data-testid="stVerticalBlockBorderWrapper"] {background:linear-gradient(180deg,rgba(9,20,39,.94),rgba(5,12,25,.93));border:1px solid var(--line)!important;border-radius:28px!important;box-shadow:0 14px 38px rgba(0,0,0,.22);transition:all .18s ease;}
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {border-color:rgba(255,255,255,.13)!important;box-shadow:0 18px 46px rgba(0,0,0,.29);}
    .pill {display:inline-flex;align-items:center;gap:8px;padding:5px 11px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid var(--line);color:#cbd5e1;font-size:.79rem;font-weight:800;margin-bottom:12px;}
    .product-title {font-size:1.75rem;font-weight:950;line-height:1.1}.product-sub {color:#94a3b8;font-size:.92rem;margin-top:6px}.section-kicker {font-size:.73rem;font-weight:900;letter-spacing:.14em;color:#fda4af;margin-bottom:8px}.price {font-size:1.95rem;font-weight:950;line-height:1.1}.sub {color:#94a3b8;font-size:.84rem;line-height:1.62}.deal {margin-top:10px;padding:10px 12px;border-radius:16px;background:rgba(255,91,112,.075);border:1px solid rgba(255,91,112,.18);font-weight:800}.empty {border:1px dashed var(--line);border-radius:18px;padding:14px;color:#94a3b8;font-size:.88rem;min-height:96px;background:rgba(255,255,255,.02)}
    </style>
    """,
    unsafe_allow_html=True,
)

if not Path(DB).exists():
    run_ingestion()

with sqlite3.connect(DB) as conn:
    fx = pd.read_sql_query("SELECT * FROM fx_rates ORDER BY observed_at DESC LIMIT 1", conn)
    prices = pd.read_sql_query(
        """
        SELECT p.* FROM price_observations p
        JOIN (SELECT product_id, source, MAX(observed_at) mx FROM price_observations GROUP BY product_id, source) q
        ON p.product_id=q.product_id AND p.source=q.source AND p.observed_at=q.mx
        """, conn
    )

with open("config/products.yaml", "r", encoding="utf-8") as f:
    products = yaml.safe_load(f)["products"]

fx_rate = float(fx.iloc[0]["rate"]) if not fx.empty else 0.0

st.markdown(
    f"""
    <div class="hero">
      <div class="eyebrow">TOKYO TECH HUNT / JAPAN ⇄ TAIWAN</div>
      <h1>JP–TW Gadget Price Radar 🗼</h1>
      <p>把赴日買 3C 變成一件更像「逛街」的事。新品、二手、匯率與公開零售行情放在同一個畫面，快速看出 <b>現在在哪裡買比較值得</b>。</p>
      <div class="chip-row"><span class="chip">💱 1 JPY ≈ {fx_rate:.5f} TWD</span><span class="chip">🧳 Tourist-first</span><span class="chip">🎧 Apple · Nintendo · PlayStation</span><span class="chip">♻️ New + Used</span></div>
    </div>
    """, unsafe_allow_html=True
)

with st.sidebar:
    st.markdown("## ✦ Tokyo Tech Hunt")
    st.caption("東京で買う？台湾で買う？")
    segments = sorted({p.get("segment", "Other") for p in products})
    families = sorted({p["family"] for p in products})
    segment = st.selectbox("品類", ["全部"] + segments)
    family = st.selectbox("系列", ["全部"] + families)
    mode = st.radio("比較模式", ["全部", "新品", "中古"], horizontal=True)
    if st.button("↻ 更新今日價格", use_container_width=True):
        with st.spinner("正在逛日本公開零售頁面…"):
            result = run_ingestion()
        st.success(f"更新完成 · {result['observations']} 筆")
        st.rerun()

filtered = [p for p in products if (segment == "全部" or p.get("segment", "Other") == segment) and (family == "全部" or p["family"] == family)]

summary_cols = st.columns(4)
summary_values = [("TRACKED MODELS", len(filtered)), ("PUBLIC SOURCES", prices["source"].nunique() if not prices.empty else 0), ("JPY / TWD", f"{fx_rate:.5f}"), ("CATEGORIES", len({p.get('segment', 'Other') for p in filtered}))]
for col, (label, value) in zip(summary_cols, summary_values):
    with col:
        st.markdown(f'<div class="stat-card"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>', unsafe_allow_html=True)

ranked = compute_top_deals(filtered, prices)[:3]
if ranked:
    st.markdown("## 🔥 今日值得看")
    st.caption("依目前可取得的日本／台灣公開價格，先把價差最大的項目推到前面。")
    cols = st.columns(len(ranked))
    for col, item in zip(cols, ranked):
        p = item["product"]
        cls = deal_class(item["pct"])
        icon = SEGMENT_ICONS.get(p.get("segment", "Other"), "✨")
        card_html = (
            f'<div class="deal-card {cls}">'
            f'<div class="deal-ribbon">{icon} {item["mode"]} · {p.get("family")}</div>'
            f'<div class="deal-name">{product_title(p)}</div>'
            f'<div class="deal-pct">{item["pct"]:+.1f}%</div>'
            f'<div class="deal-meta">{item["verdict"]}<br>日本約 NT${item["japan_twd"]:,} · 台灣約 NT${item["taiwan_twd"]:,}</div>'
            '</div>'
        )
        with col:
            st.markdown(card_html, unsafe_allow_html=True)

st.markdown("## 今日公開比價")
st.caption("新品用官方定價當基準；中古／未使用則比較日本公開零售來源。")

for product in filtered:
    rows = prices[prices["product_id"] == product["id"]].copy()
    icon = SEGMENT_ICONS.get(product.get("segment", "Other"), "✨")
    jp_label = SEGMENT_JP.get(product.get("segment", "Other"), "ガジェット")

    with st.container(border=True):
        st.markdown(f'<div class="pill">{icon} {product.get("segment", "Other")} · {jp_label}</div><div class="product-title">{product_title(product)}</div><div class="product-sub">{product_subtitle(product)}</div>', unsafe_allow_html=True)

        if mode in ("全部", "新品"):
            new_jp = rows[(rows["condition"] == "new") & (rows["source_country"] == "JP")]
            new_tw = rows[(rows["condition"] == "new") & (rows["source_country"] == "TW")]
            if not new_jp.empty or not new_tw.empty:
                st.markdown("#### ✨ 新品官方對照")
                c1, c2, c3 = st.columns([1.45, 1.45, 1.1])
                jp_twd = float(new_jp.iloc[0]["price_twd"]) if not new_jp.empty else None
                tw_twd = float(new_tw.iloc[0]["price_twd"]) if not new_tw.empty else None
                new_deal = savings(jp_twd, tw_twd)
                with c1:
                    st.markdown('<div class="section-kicker">🇯🇵 OFFICIAL JAPAN</div>', unsafe_allow_html=True)
                    if not new_jp.empty:
                        r = new_jp.iloc[0]
                        st.markdown(f'<div class="price">¥{safe_int(r["price"]):,}</div><div class="sub">≈ NT${safe_int(r["price_twd"]):,}<br>{r["source"]}</div>', unsafe_allow_html=True)
                        st.link_button("日本官方 ↗", r["url"], use_container_width=True)
                    else:
                        st.markdown('<div class="empty">今日沒有日本官方對照。</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div class="section-kicker">🇹🇼 OFFICIAL TAIWAN</div>', unsafe_allow_html=True)
                    if not new_tw.empty:
                        r = new_tw.iloc[0]
                        st.markdown(f'<div class="price">NT${safe_int(r["price_twd"]):,}</div><div class="sub">{r["source"]}</div>', unsafe_allow_html=True)
                        st.link_button("台灣官方 ↗", r["url"], use_container_width=True)
                    else:
                        st.markdown('<div class="empty">今日沒有台灣官方對照。</div>', unsafe_allow_html=True)
                with c3:
                    st.markdown('<div class="section-kicker">NEW DEAL CHECK</div>', unsafe_allow_html=True)
                    if new_deal:
                        st.markdown(f'<div class="price">{new_deal["pct"]:+.1f}%</div><div class="deal">{new_deal["verdict"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="empty">缺少其中一地官方價格。</div>', unsafe_allow_html=True)

        if mode in ("全部", "中古"):
            used_jp = rows[(rows["source_country"] == "JP") & (rows["source"].isin(JAPAN_USED)) & (rows["condition"].isin(["used", "unused", "unknown"]))].copy()
            tw_ref = rows[rows["source"] == "US3C Market Avg"]
            if not used_jp.empty or not tw_ref.empty:
                st.markdown("#### ♻️ 日本公開二手／未使用行情")
                store_cols = st.columns(3)
                for col, source in zip(store_cols, JAPAN_USED):
                    with col:
                        one = used_jp[used_jp["source"] == source]
                        st.markdown(f'<div class="section-kicker">🇯🇵 {source.upper()}</div>', unsafe_allow_html=True)
                        if one.empty:
                            st.markdown('<div class="empty">今日未取得</div>', unsafe_allow_html=True)
                        else:
                            r = one.sort_values("price_twd").iloc[0]
                            st.markdown(f'<div class="price">¥{safe_int(r["price"]):,}</div><div class="sub">≈ NT${safe_int(r["price_twd"]):,}<br>{r["condition"]} · {r["note"]}</div>', unsafe_allow_html=True)
                            st.link_button(f"開啟 {source} ↗", r["url"], use_container_width=True)
                jp_best = used_jp.sort_values("price_twd").iloc[0] if not used_jp.empty else None
                tw_ref_twd = float(tw_ref.iloc[0]["price_twd"]) if not tw_ref.empty else None
                jp_best_twd = float(jp_best["price_twd"]) if jp_best is not None else None
                used_deal = savings(jp_best_twd, tw_ref_twd)
                d1, d2, d3 = st.columns([1.45, 1.45, 1.1])
                with d1:
                    st.markdown('<div class="section-kicker">🏆 JAPAN BEST PUBLIC PRICE</div>', unsafe_allow_html=True)
                    if jp_best is not None:
                        st.markdown(f'<div class="price">NT${safe_int(jp_best["price_twd"]):,}</div><div class="sub">{jp_best["source"]}<br>{jp_best["raw_title"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="empty">今天沒有可用日本中古資料。</div>', unsafe_allow_html=True)
                with d2:
                    st.markdown('<div class="section-kicker">🇹🇼 TAIWAN PUBLIC REFERENCE</div>', unsafe_allow_html=True)
                    if not tw_ref.empty:
                        ref = tw_ref.iloc[0]
                        st.markdown(f'<div class="price">NT${safe_int(ref["price_twd"]):,}</div><div class="sub">{ref["source"]}<br>{ref["note"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="empty">此產品目前沒有台灣二手公開參考。</div>', unsafe_allow_html=True)
                with d3:
                    st.markdown('<div class="section-kicker">USED DEAL CHECK</div>', unsafe_allow_html=True)
                    if used_deal:
                        st.markdown(f'<div class="price">{used_deal["pct"]:+.1f}%</div><div class="deal">{used_deal["verdict"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="empty">缺少台灣公開參考，暫不判斷。</div>', unsafe_allow_html=True)

st.caption("正式購買前仍需確認：機況、語言／區域版本、保固、配件、庫存與日本免稅資格。")
