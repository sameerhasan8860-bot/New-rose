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
                assert result["warnings"] == 2
                assert result["reports"] == 1
                assert result["actions"] == 1
                assert result["notes"] == 0
                assert result["filters"] == 0
                assert result["blocked_terms"] == 0
                assert result["captcha_challenges"] == 0
            async with session.begin():
                from sqlalchemy import select
                remaining = (await session.scalars(select(WarningRecord))).all()
                assert len(remaining) == 1
                assert remaining[0].chat_id == -3002
        await db.close()
    asyncio.run(scenario())
