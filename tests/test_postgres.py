import asyncio
import os

import pytest
from sqlalchemy import select

from app.db.engine import Database
from app.db.models import UpdateClaim
from app.db.repositories import claim_update


@pytest.mark.skipif(not os.getenv("POSTGRES_TEST_URL"), reason="POSTGRES_TEST_URL is not configured")
def test_postgres_concurrent_update_claim_insert_is_unique():
    async def scenario():
        db = Database(os.environ["POSTGRES_TEST_URL"])
        async with db.sessions() as session:
            async with session.begin():
                await session.execute(select(UpdateClaim).limit(1))
        async def attempt():
            async with db.sessions() as session:
                async with session.begin():
                    return await claim_update(session, 987654321, f'owner-{id(asyncio.current_task())}', lease_seconds=300)
        results = await asyncio.gather(*(attempt() for _ in range(12)))
        assert sum(results) == 1
        async with db.sessions() as session:
            row = await session.get(UpdateClaim, 987654321)
            assert row is not None
        await db.close()
    asyncio.run(scenario())
