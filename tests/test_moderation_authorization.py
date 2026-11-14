import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.enums import ChatMemberStatus

import app.handlers as handlers


def _message():
    return SimpleNamespace(
        chat=SimpleNamespace(id=-100123, type="supergroup"),
        from_user=SimpleNamespace(id=10),
        reply_to_message=SimpleNamespace(from_user=SimpleNamespace(
            id=20, is_bot=False, full_name="Target User"
        )),
        answer=AsyncMock(),
    )


def _member(status=ChatMemberStatus.ADMINISTRATOR, **rights):
    return SimpleNamespace(status=status, **rights)


def test_moderation_denies_non_admin(monkeypatch):
    async def scenario():
        message = _message()
        bot = SimpleNamespace(get_chat_member=AsyncMock())
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=False))

        result = await handlers._moderation_context(message, bot)

        assert result is None
        message.answer.assert_awaited_once()
        bot.get_chat_member.assert_not_awaited()
    asyncio.run(scenario())


def test_moderation_requires_actor_ban_permission(monkeypatch):
    async def scenario():
        message = _message()
        bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=_member(can_restrict_members=False)))
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=True))

        result = await handlers._moderation_context(message, bot)

        assert result is None
        assert "Ban users" in message.answer.await_args.args[0]
        bot.get_chat_member.assert_awaited_once_with(message.chat.id, message.from_user.id)
    asyncio.run(scenario())


def test_moderation_requires_bot_ban_permission(monkeypatch):
    async def scenario():
        message = _message()
        bot = SimpleNamespace(
            get_chat_member=AsyncMock(side_effect=[
                _member(can_restrict_members=True),
                _member(status=ChatMemberStatus.MEMBER),
                _member(can_restrict_members=False),
            ]),
            get_me=AsyncMock(return_value=SimpleNamespace(id=99)),
        )
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=True))

        result = await handlers._moderation_context(message, bot)

        assert result is None
        assert "I need" in message.answer.await_args.args[0]
        assert bot.get_chat_member.await_count == 3
    asyncio.run(scenario())


def test_moderation_accepts_admin_and_bot_with_ban_permission(monkeypatch):
    async def scenario():
        message = _message()
        bot = SimpleNamespace(
            get_chat_member=AsyncMock(side_effect=[
                _member(can_restrict_members=True),
                _member(status=ChatMemberStatus.MEMBER),
                _member(can_restrict_members=True),
            ]),
            get_me=AsyncMock(return_value=SimpleNamespace(id=99)),
        )
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=True))

        result = await handlers._moderation_context(message, bot)

        assert result is not None
        actor, target = result
        assert actor.id == 10
        assert target.id == 20
        message.answer.assert_not_awaited()
    asyncio.run(scenario())


def test_moderation_rejects_bot_as_actor(monkeypatch):
    async def scenario():
        message = _message()
        message.from_user.is_bot = True
        bot = SimpleNamespace(get_chat_member=AsyncMock())
        monkeypatch.setattr(handlers, "has_group_admin_rights", AsyncMock(return_value=True))
        result = await handlers._moderation_context(message, bot)
        assert result is None
        bot.get_chat_member.assert_not_awaited()
        message.answer.assert_awaited_once()
    asyncio.run(scenario())
