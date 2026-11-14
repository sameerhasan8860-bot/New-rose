import asyncio
import os

import pytest
from sqlalchemy import select

from app.db.engine import Database
from app.db.models import ProcessedUpdate
from app.db.repositories import mark_update_processed


@pytest.mark.skipif(not os.getenv("POSTGRES_TEST_URL"), reason="POSTGRES_TEST_URL is not configured")
def test_postgres_concurrent_update_claim_insert_is_unique():
    async def scenario():
        db = Database(os.environ["POSTGRES_TEST_URL"])
        async with db.sessions() as session:
            async with session.begin():
                await session.execute(select(ProcessedUpdate).limit(1))
        async def attempt():
            async with db.sessions() as session:
                async with session.begin():
                    return await mark_update_processed(session, 987654321)
        results = await asyncio.gather(*(attempt() for _ in range(12)))
        assert sum(results) == 1
        async with db.sessions() as session:
            row = await session.get(ProcessedUpdate, 987654321)
            assert row is not None
        await db.close()
    asyncio.run(scenario())
