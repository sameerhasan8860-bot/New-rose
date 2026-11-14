import asyncio
import pytest
from app.db.engine import Database
from app.db.repositories import GroupRepository, mark_update_processed


def test_group_settings_are_isolated_by_chat_id():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        repo = GroupRepository()
        async with db.sessions() as session:
            async with session.begin():
                await repo.set_setting(session, -1001, "welcome", {"enabled": True})
                await repo.set_setting(session, -1002, "welcome", {"enabled": False})
        async with db.sessions() as session:
            assert await repo.get_setting(session, -1001, "welcome") == {"enabled": True}
            assert await repo.get_setting(session, -1002, "welcome") == {"enabled": False}
        await db.close()
    asyncio.run(scenario())


def test_update_deduplication():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                assert await mark_update_processed(session, 777) is True
            async with session.begin():
                assert await mark_update_processed(session, 777) is False
        await db.close()
    asyncio.run(scenario())


def test_command_registry_only_lists_real_core_commands():
    from app.services.command_registry import COMMAND_MAP, get_command
    assert get_command("/help").name == "help"
    assert get_command("not-a-command") is None
    assert set(COMMAND_MAP) == {"start", "help", "settings", "about", "id", "ping", "status", "ban", "unban", "kick", "mute", "unmute", "warn", "warnings"}
