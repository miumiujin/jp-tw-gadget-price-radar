from apple_radar.compare import savings


def test_japan_cheaper():
    result = savings(20000, 25000)
    assert result["amount"] == 5000
    assert result["pct"] == 20.0
    assert "日本" in result["verdict"]


def test_taiwan_cheaper():
    result = savings(26000, 25000)
    assert result["amount"] == -1000
    assert result["pct"] == -4.0
    assert "台灣" in result["verdict"]
