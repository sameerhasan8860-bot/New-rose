import asyncio
from app.db.engine import Database
from app.db.models import BlockedTerm, Group, GroupFilter, Note, ReportRecord
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


def test_blocked_terms_are_group_scoped():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                session.add_all([Group(chat_id=-3001, title="A"), Group(chat_id=-3002, title="B")])
            async with session.begin():
                session.add(BlockedTerm(chat_id=-3001, term="scam", creator_id=7))
            async with session.begin():
                from sqlalchemy import select
                a = (await session.scalars(select(BlockedTerm).where(BlockedTerm.chat_id == -3001))).all()
                b = (await session.scalars(select(BlockedTerm).where(BlockedTerm.chat_id == -3002))).all()
                assert [item.term for item in a] == ["scam"]
                assert b == []
        await db.close()
    asyncio.run(scenario())


def test_update_middleware_does_not_mark_failed_handler_as_processed():
    async def scenario():
        from aiogram.types import Update
        from app.db.middleware import UpdateDeduplicationMiddleware
        from app.db.models import ProcessedUpdate
        from sqlalchemy import select
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        middleware = UpdateDeduplicationMiddleware(db)
        event = Update(update_id=991)
        calls = {"count": 0}

        async def failing_handler(event, data):
            calls["count"] += 1
            raise RuntimeError("temporary failure")

        try:
            await middleware(failing_handler, event, {})
        except RuntimeError:
            pass
        async with db.sessions() as session:
            assert await session.get(ProcessedUpdate, 991) is None

        async def successful_handler(event, data):
            calls["count"] += 1
            return "ok"

        assert await middleware(successful_handler, event, {}) == "ok"
        async with db.sessions() as session:
            assert await session.get(ProcessedUpdate, 991) is not None
        assert calls["count"] == 2
        await db.close()
    asyncio.run(scenario())


def test_captcha_challenges_are_persisted_and_group_scoped():
    async def scenario():
        from datetime import datetime, timedelta, timezone
        from app.db.models import CaptchaChallenge, Group
        from sqlalchemy import select
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                session.add_all([Group(chat_id=-4101, title="A"), Group(chat_id=-4102, title="B")])
            async with session.begin():
                session.add(CaptchaChallenge(chat_id=-4101, user_id=91, answer=7, choices_json="[7,8,6]", expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
            async with db.sessions() as check:
                rows = (await check.scalars(select(CaptchaChallenge).where(CaptchaChallenge.chat_id == -4101))).all()
                other = (await check.scalars(select(CaptchaChallenge).where(CaptchaChallenge.chat_id == -4102))).all()
                assert len(rows) == 1 and rows[0].answer == 7 and rows[0].status == "pending"
                assert other == []
        await db.close()
    asyncio.run(scenario())



def test_update_claim_is_exclusive_and_released_after_handler_failure():
    async def scenario():
        from app.db.repositories import claim_update, release_update_claim
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                assert await claim_update(session, 12001, "owner-a", lease_seconds=300) is True
        async with db.sessions() as session:
            async with session.begin():
                assert await claim_update(session, 12001, "owner-b", lease_seconds=300) is False
        async with db.sessions() as session:
            async with session.begin():
                await release_update_claim(session, 12001, "owner-a")
        async with db.sessions() as session:
            async with session.begin():
                assert await claim_update(session, 12001, "owner-b", lease_seconds=300) is True
        await db.close()
    asyncio.run(scenario())
