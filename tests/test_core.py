from app.handlers import BRAND

def test_brand_is_present():
    assert "MASTER" in BRAND
    assert "X" in BRAND

def test_brand_is_not_empty():
    assert len(BRAND) > 5
