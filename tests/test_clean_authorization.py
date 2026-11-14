import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.enums import ChatMemberStatus, ChatType

import app.handlers as handlers


def _message():
    return SimpleNamespace(
        chat=SimpleNamespace(id=-5001, type=ChatType.SUPERGROUP),
        from_user=SimpleNamespace(id=50, is_bot=False),
        message_id=120,
        text="/clean 3",
        answer=AsyncMock(),
    )


def _member(can_delete):
    return SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR, can_delete_messages=can_delete)


def test_clean_requires_current_admin(monkeypatch):
    async def scenario():
        message = _message()
        bot = SimpleNamespace(get_chat_member=AsyncMock(), get_me=AsyncMock(), delete_messages=AsyncMock())
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=False))
        await handlers.clean_messages(message, bot)
        bot.delete_messages.assert_not_awaited()
    asyncio.run(scenario())


def test_clean_requires_bot_delete_permission(monkeypatch):
    async def scenario():
        message = _message()
        bot = SimpleNamespace(
            get_chat_member=AsyncMock(side_effect=[_member(True), _member(False)]),
            get_me=AsyncMock(return_value=SimpleNamespace(id=99)),
            delete_messages=AsyncMock(),
        )
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=True))
        await handlers.clean_messages(message, bot)
        bot.delete_messages.assert_not_awaited()
        message.answer.assert_awaited_once()
    asyncio.run(scenario())


def test_clean_deletes_only_bounded_requested_message_ids(monkeypatch):
    async def scenario():
        message = _message()
        bot = SimpleNamespace(
            get_chat_member=AsyncMock(side_effect=[_member(True), _member(True)]),
            get_me=AsyncMock(return_value=SimpleNamespace(id=99)),
            delete_messages=AsyncMock(return_value=True),
        )
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=True))
        await handlers.clean_messages(message, bot)
        bot.delete_messages.assert_awaited_once_with(-5001, [118, 119, 120])
    asyncio.run(scenario())
