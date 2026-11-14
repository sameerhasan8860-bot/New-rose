import asyncio

from app.db.engine import Database
from app.db.models import Group, ModerationAction, ReportRecord, WarningRecord
from app.services.privacy import erase_user_group_records


def test_privacy_erasure_is_limited_to_requesting_user_and_group():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                session.add_all([Group(chat_id=-3001, title="A"), Group(chat_id=-3002, title="B")])
            async with session.begin():
                session.add_all([
                    WarningRecord(chat_id=-3001, user_id=7, actor_id=9, reason="target"),
                    WarningRecord(chat_id=-3001, user_id=8, actor_id=7, reason="actor"),
                    WarningRecord(chat_id=-3002, user_id=7, actor_id=9, reason="other group"),
                    ReportRecord(chat_id=-3001, reporter_id=7, target_id=8, message_id=1, reason="report"),
                    ModerationAction(chat_id=-3001, actor_id=7, target_id=8, action="ban", reason="audit"),
                ])
            async with session.begin():
                result = await erase_user_group_records(session, chat_id=-3001, user_id=7)
                assert result["warnings"] == 2\n                assert result["reports"] == 1\n                assert result["actions"] == 1\n                assert result["notes"] == result["filters"] == result["blocked_terms"] == result["captcha_challenges"] == 0
            async with session.begin():
                from sqlalchemy import select
                assert len((await session.scalars(select(WarningRecord))).all()) == 1
                remaining = (await session.scalars(select(WarningRecord))).first()
                assert remaining.chat_id == -3002
        await db.close()
    asyncio.run(scenario())
