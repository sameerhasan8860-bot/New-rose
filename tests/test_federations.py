import asyncio

import pytest

from app.db.engine import Database
from app.services.federations import create_federation, federation_members, join_federation, leave_federation


def test_federation_membership_requires_explicit_group_opt_in_and_isolated():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                federation = await create_federation(session, name="community", chat_id=-1001, actor_id=11)
                federation_id = federation.id
            async with session.begin():
                await join_federation(session, federation_id=federation_id, chat_id=-1002, actor_id=22)
            async with session.begin():
                assert await federation_members(session, federation_id) == [-1001, -1002]
                assert await leave_federation(session, chat_id=-1002) is True
            async with session.begin():
                assert await federation_members(session, federation_id) == [-1001]
                assert await leave_federation(session, chat_id=-1002) is False
        await db.close()
    asyncio.run(scenario())


def test_group_cannot_join_two_federations_and_duplicate_join_is_rejected():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                alpha = await create_federation(session, name="alpha", chat_id=-2001, actor_id=1)
                beta = await create_federation(session, name="beta", chat_id=-2002, actor_id=2)
                alpha_id, beta_id = alpha.id, beta.id
            with pytest.raises(ValueError, match="already opted in"):
                async with session.begin():
                    await join_federation(session, federation_id=alpha_id, chat_id=-2001, actor_id=1)
            with pytest.raises(ValueError, match="another federation"):
                async with session.begin():
                    await join_federation(session, federation_id=beta_id, chat_id=-2001, actor_id=1)
        await db.close()
    asyncio.run(scenario())


def test_federation_ban_ledger_is_scoped_to_federation_and_can_be_revoked():
    from app.db.models import FederationBan
    from app.services.federations import record_federation_ban, remove_federation_ban

    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                one = await create_federation(session, name="one", chat_id=-3001, actor_id=1)
                two = await create_federation(session, name="two", chat_id=-3002, actor_id=2)
                one_id, two_id = one.id, two.id
            async with session.begin():
                await record_federation_ban(session, federation_id=one_id, user_id=99,
                                            actor_chat_id=-3001, actor_id=7, reason="spam")
            async with session.begin():
                assert await federation_ban_exists(session, federation_id=one_id, user_id=99)
                assert not await federation_ban_exists(session, federation_id=two_id, user_id=99)
                assert await remove_federation_ban(session, federation_id=one_id, user_id=99)
            async with session.begin():
                assert not await federation_ban_exists(session, federation_id=one_id, user_id=99)
        await db.close()
    from app.services.federations import federation_ban_exists
    asyncio.run(scenario())


def test_repeated_federation_ban_updates_reason_without_duplicate_rows():
    from app.db.models import FederationBan
    from app.services.federations import record_federation_ban

    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                fed = await create_federation(session, name="repeat", chat_id=-4001, actor_id=1)
                fed_id = fed.id
            async with session.begin():
                await record_federation_ban(session, federation_id=fed_id, user_id=123,
                                            actor_chat_id=-4001, actor_id=2, reason="first")
            async with session.begin():
                await record_federation_ban(session, federation_id=fed_id, user_id=123,
                                            actor_chat_id=-4001, actor_id=3, reason="updated")
            async with session.begin():
                rows = (await session.scalars(select(FederationBan).where(
                    FederationBan.federation_id == fed_id, FederationBan.user_id == 123
                ))).all()
                assert len(rows) == 1
                assert rows[0].reason == "updated"
                assert rows[0].actor_id == 3
        await db.close()
    from sqlalchemy import select
    asyncio.run(scenario())


def test_only_owner_group_can_rename_or_delete_federation():
    from app.services.federations import delete_federation, rename_federation

    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        async with db.sessions() as session:
            async with session.begin():
                fed = await create_federation(session, name="owned", chat_id=-5001, actor_id=1)
                fed_id = fed.id
            with pytest.raises(PermissionError, match="owner group"):
                async with session.begin():
                    await rename_federation(session, federation_id=fed_id, owner_chat_id=-5002, name="hijack")
            with pytest.raises(PermissionError, match="owner group"):
                async with session.begin():
                    await delete_federation(session, federation_id=fed_id, owner_chat_id=-5002)
            async with session.begin():
                renamed = await rename_federation(session, federation_id=fed_id, owner_chat_id=-5001, name="renamed")
                assert renamed.name == "renamed"
            async with session.begin():
                assert await delete_federation(session, federation_id=fed_id, owner_chat_id=-5001)
                assert await session.get(Federation, fed_id) is None
        await db.close()
    from app.db.models import Federation
    asyncio.run(scenario())
