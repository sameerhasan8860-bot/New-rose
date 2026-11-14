from app.handlers import _parse_duration
from datetime import timedelta


def test_parse_duration_units():
    assert _parse_duration("10m") == timedelta(minutes=10)
    assert _parse_duration("2h") == timedelta(hours=2)
    assert _parse_duration("1d") == timedelta(days=1)
    assert _parse_duration("30s") == timedelta(seconds=30)


def test_parse_duration_rejects_invalid_or_unsafe_values():
    assert _parse_duration("0m") is None
    assert _parse_duration("-5m") is None
    assert _parse_duration("999d") is None
    assert _parse_duration("forever") is None
