import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.enums import ChatMemberStatus

from app.services.authorization import has_group_admin_rights


def test_live_group_admin_authorization_uses_telegram_membership():
    async def scenario():
        bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR)))
        assert await has_group_admin_rights(bot, -100123, 42) is True
        bot.get_chat_member.assert_awaited_once_with(-100123, 42)
    asyncio.run(scenario())


def test_live_group_admin_authorization_rejects_members_and_left_users():
    async def scenario():
        for status in (ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED, ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
            bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=SimpleNamespace(status=status)))
            assert await has_group_admin_rights(bot, -100123, 42) is False
    asyncio.run(scenario())


def test_group_creator_is_authorized():
    async def scenario():
        bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.CREATOR)))
        assert await has_group_admin_rights(bot, -100123, 42) is True
    asyncio.run(scenario())
