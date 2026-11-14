"""Safe Telegram HTML formatting helpers."""
import html

STYLES = {"bold", "italic", "code", "quote"}


def format_text(style: str, value: str) -> str:
    style = style.lower().strip()
    value = value.strip()
    if style not in STYLES:
        raise ValueError("Choose bold, italic, code, or quote.")
    if not value or len(value) > 3500:
        raise ValueError("Text must contain 1–3,500 characters.")
    escaped = html.escape(value)
    if style == "bold":
        return f"<b>{escaped}</b>"
    if style == "italic":
        return f"<i>{escaped}</i>"
    if style == "code":
        return f"<code>{escaped}</code>"
    return f"<blockquote>{escaped}</blockquote>"
