from apple_radar.sources.janpara import parse_janpara_html
from apple_radar.sources.iosys import parse_iosys_html
from apple_radar.sources.sofmap import parse_sofmap_html


MAC = {
    "required_groups": [
        ["MacBook Air"],
        ["M2"],
        ["13インチ", "13.6-inch"],
        ["8GB", "8G"],
        ["256GB", "256G", "SSD256GB"],
    ],
    "forbidden_tokens": ["16GB", "16G", "ケース"],
}

IPAD = {
    "required_groups": [
        ["iPad Air"],
        ["M2", "第6世代"],
        ["11インチ"],
        ["128GB"],
        ["Wi-Fi"],
    ],
    "forbidden_tokens": ["Cellular", "256GB"],
}


def test_janpara_parser():
    html = """
    <html><body>
    Apple MacBook Air 13インチ M2(CPU:8C/GPU:8C) 8GB/256GB ミッドナイト MLY33J/A (M2,2022)
    41個の在庫
    中古 ¥79,980～
    Apple MacBook Air 13インチ M2 16GB/256GB シルバー
    3個の在庫
    中古 ¥109,980～
    </body></html>
    """
    rows = parse_janpara_html(html, MAC)
    assert rows[0]["price_jpy"] == 79980
    assert rows[0]["stock"] == 41


def test_iosys_parser():
    html = """
    <html><body>
    128GB Wi-Fiモデル 〖第6世代〗 iPad Air(M2) 11インチ Wi-Fi 128GB ブルー MUWD3J/A
    メーカー：Apple 発売日：2024/05 付属品: 本体のみ 在庫数：1 中古Aランク 82,800円 (税込)
    256GB Wi-Fiモデル 〖第6世代〗 iPad Air(M2) 11インチ Wi-Fi 256GB
    在庫数：1 中古Bランク 94,800円 (税込)
    </body></html>
    """
    rows = parse_iosys_html(html, IPAD)
    assert len(rows) == 1
    assert rows[0]["price_jpy"] == 82800
    assert rows[0]["rank"] == "中古Aランク"


def test_sofmap_parser():
    html = """
    <div class="item">
      <a href="/product_detail.aspx?sku=415287311">
        〔中古品〕 MacBook Air 13.6-inch Mid-2022 MLXY3J／A Apple M2
        8コアCPU_8コアGPU 8GB SSD256GB シルバー
      </a>
      <div>中古商品ランク B：良品</div>
      <div>ソフマップ特価 ¥99,980(税込)</div>
    </div>
    <div class="item">
      <a href="/product_detail.aspx?sku=999">
        〔中古品〕 MacBook Air 13.6-inch M2 16GB SSD256GB
      </a>
      <div>¥120,000(税込)</div>
    </div>
    """
    rows = parse_sofmap_html(html, MAC)
    assert len(rows) == 1
    assert rows[0].price_jpy == 99980
    assert rows[0].rank == "B"
