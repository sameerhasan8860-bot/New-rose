import asyncio
from app.db.engine import Database
from app.db.models import Group, GroupFilter, Note, ReportRecord
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


def test_notes_and_filters_are_isolated_by_group():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                session.add_all([Group(chat_id=-2001, title="A"), Group(chat_id=-2002, title="B")])
            async with session.begin():
                session.add(Note(chat_id=-2001, name="rules", content="Be kind", creator_id=1))
                session.add(GroupFilter(chat_id=-2001, trigger="hello", response="Welcome", creator_id=1))
                session.add(Note(chat_id=-2002, name="rules", content="Other rules", creator_id=2))
            async with session.begin():
                from sqlalchemy import select
                notes_a = (await session.scalars(select(Note).where(Note.chat_id == -2001))).all()
                filters_b = (await session.scalars(select(GroupFilter).where(GroupFilter.chat_id == -2002))).all()
                assert len(notes_a) == 1 and notes_a[0].content == "Be kind"
                assert filters_b == []
        await db.close()
    asyncio.run(scenario())
