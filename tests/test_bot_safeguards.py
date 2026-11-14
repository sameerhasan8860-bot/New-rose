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
