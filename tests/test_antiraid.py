import asyncio
from datetime import datetime, timedelta, timezone

from app.db.engine import Database
from app.services.antiraid import record_join_and_claim_alert


def test_antiraid_threshold_is_persistent_and_alert_is_claimed_once():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        start = datetime.now(timezone.utc)
        async with db.sessions() as session:
            async with session.begin():
                for index in range(4):
                    assert await record_join_and_claim_alert(
                        session, chat_id=-4001, user_id=100 + index, now=start + timedelta(seconds=index)
                    ) is False
            async with session.begin():
                assert await record_join_and_claim_alert(
                    session, chat_id=-4001, user_id=104, now=start + timedelta(seconds=4)
                ) is True
            async with session.begin():
                assert await record_join_and_claim_alert(
                    session, chat_id=-4001, user_id=105, now=start + timedelta(seconds=5)
                ) is False
            async with session.begin():
                # A different group has an independent threshold window.
                assert await record_join_and_claim_alert(
                    session, chat_id=-4002, user_id=201, now=start + timedelta(seconds=5)
                ) is False
        await db.close()
    asyncio.run(scenario())
