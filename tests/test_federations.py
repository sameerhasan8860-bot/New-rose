import asyncio

import pytest
from sqlalchemy import select

from app.db.engine import Database
from app.db.models import FederationGroup
from app.services.federations import create_federation, federation_members, join_federation, leave_federation


def test_federation_membership_requires_explicit_group_opt_in_and_isolated():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                fed = await create_federation(session, name="community", chat_id=-1001, actor_id=11)\n                federation_id = fed.id
            async with session.begin():
                await join_federation(session, federation_id=federation_id, chat_id=-1002, actor_id=22)
            async with session.begin():
                assert await federation_members(session, federation_id) == [-1001, -1002]
                assert await leave_federation(session, chat_id=-1002) is True
            async with session.begin():
                assert await federation_members(session, fed.id) == [-1001]
                assert await leave_federation(session, chat_id=-1002) is False
        await db.close()
    asyncio.run(scenario())


def test_group_cannot_join_two_federations_and_duplicate_join_is_rejected():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                a = await create_federation(session, name="alpha", chat_id=-2001, actor_id=1)
                b = await create_federation(session, name="beta", chat_id=-2002, actor_id=2)
            with pytest.raises(ValueError, match="already opted in"):
                async with session.begin():
                    await join_federation(session, federation_id=a_id, chat_id=-2001, actor_id=1)
            with pytest.raises(ValueError, match="another federation"):
                async with session.begin():
                    await join_federation(session, federation_id=b_id, chat_id=-2001, actor_id=1)
        await db.close()
    asyncio.run(scenario())
