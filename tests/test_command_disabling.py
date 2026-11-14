import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Chat, Message, User

from app.db.engine import Database
from app.db.models import Group
from app.db.repositories import GroupRepository
from app.services.command_disabling import CommandDisablingMiddleware


def _message(command: str, *, user_id: int = 10):
    msg = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=Chat(id=-100123, type="supergroup", title="test"),
        from_user=User(id=user_id, is_bot=False, first_name="Tester"),
        text=f"/{command}",
    )
    object.__setattr__(msg, "answer", AsyncMock())
    return msg


def test_disabled_command_is_blocked_for_regular_members():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                await GroupRepository().set_setting(session, -100123, "disabled_commands", ["ban"])
        handler = AsyncMock(return_value="called")
        middleware = CommandDisablingMiddleware()
        msg = _message("ban")
        result = await middleware(handler, msg, {"database": db, "bot": object()})
        assert result is None
        handler.assert_not_awaited()
        msg.answer.assert_awaited_once()
        await db.close()
    asyncio.run(scenario())


def test_disabled_command_allows_admin_by_default(monkeypatch):
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                await GroupRepository().set_setting(session, -100123, "disabled_commands", ["ban"])
        async def admin(*args):
            return True
        monkeypatch.setattr("app.services.authorization.has_group_admin_rights", admin)
        handler = AsyncMock(return_value="called")
        result = await CommandDisablingMiddleware()(handler, _message("ban"), {"database": db, "bot": object()})
        assert result == "called"
        handler.assert_awaited_once()
        await db.close()
    asyncio.run(scenario())


def test_disableadmin_blocks_admins_too(monkeypatch):
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                repo = GroupRepository()
                await repo.set_setting(session, -100123, "disabled_commands", ["ban"])
                await repo.set_setting(session, -100123, "disable_commands_for_admins", True)
        async def admin(*args):
            return True
        monkeypatch.setattr("app.services.authorization.has_group_admin_rights", admin)
        handler = AsyncMock(return_value="called")
        msg = _message("ban")
        result = await CommandDisablingMiddleware()(handler, msg, {"database": db, "bot": object()})
        assert result is None
        handler.assert_not_awaited()
        msg.answer.assert_awaited_once()
        await db.close()
    asyncio.run(scenario())
