from types import SimpleNamespace

from app.handlers import _allow_human_callback, _allow_human_message


def test_bot_authored_messages_are_rejected_by_default():
    assert _allow_human_message(SimpleNamespace(from_user=SimpleNamespace(is_bot=True))) is False


def test_human_messages_are_allowed():
    assert _allow_human_message(SimpleNamespace(from_user=SimpleNamespace(is_bot=False))) is True


def test_anonymous_sender_messages_fail_closed():
    assert _allow_human_message(SimpleNamespace(from_user=None)) is False


def test_bot_callbacks_are_rejected():
    assert _allow_human_callback(SimpleNamespace(from_user=SimpleNamespace(is_bot=True))) is False
    assert _allow_human_callback(SimpleNamespace(from_user=SimpleNamespace(is_bot=False))) is True


def test_rose_style_timed_ban_and_mute_duration_parser_bounds():
    from datetime import timedelta
    from app.handlers import _parse_duration

    assert _parse_duration("10m") == timedelta(minutes=10)
    assert _parse_duration("2h") == timedelta(hours=2)
    assert _parse_duration("1d") == timedelta(days=1)
    assert _parse_duration("0m") is None
    assert _parse_duration("367d") is None
    assert _parse_duration("10minutes") is None
