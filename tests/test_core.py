from app.handlers import BRAND


def test_brand_is_present():
    assert "𝗠𝗔𝗦𝗧𝗘𝗥" in BRAND
    assert "𝗫" in BRAND
