import pytest

from app.services.formatting import format_text


def test_formatting_escapes_untrusted_html():
    assert format_text("bold", "<script>hi</script>") == "<b>&lt;script&gt;hi&lt;/script&gt;</b>"
    assert format_text("code", "a & b") == "<code>a &amp; b</code>"


@pytest.mark.parametrize("style", ["bold", "italic", "code", "quote"])
def test_supported_format_styles(style):
    assert format_text(style, "hello")


def test_rejects_unknown_style_empty_and_oversized_text():
    with pytest.raises(ValueError):
        format_text("spoiler", "hello")
    with pytest.raises(ValueError):
        format_text("bold", " ")
    with pytest.raises(ValueError):
        format_text("bold", "x" * 3501)
