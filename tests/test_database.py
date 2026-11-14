import asyncio
from app.db.engine import Database
from app.db.models import Group, ReportRecord
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


def test_reports_are_group_scoped_and_persisted():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                session.add(Group(chat_id=-1001, title="One"))
                session.add(Group(chat_id=-1002, title="Two"))
            async with session.begin():
                session.add(ReportRecord(chat_id=-1001, reporter_id=10, target_id=20, message_id=30, reason="spam"))
                session.add(ReportRecord(chat_id=-1002, reporter_id=11, target_id=21, message_id=31, reason="abuse"))
            async with session.begin():
                from sqlalchemy import select
                one = (await session.scalars(select(ReportRecord).where(ReportRecord.chat_id == -1001))).all()
                two = (await session.scalars(select(ReportRecord).where(ReportRecord.chat_id == -1002))).all()
                assert len(one) == 1 and one[0].reason == "spam"
                assert len(two) == 1 and two[0].reason == "abuse"
        await db.close()
    asyncio.run(scenario())


def test_command_registry_only_lists_real_core_commands():
    from app.services.command_registry import COMMAND_MAP, get_command
    assert get_command("/help").name == "help"
    assert get_command("not-a-command") is None
    assert {"report", "reports", "adminlog"}.issubset(COMMAND_MAP)
