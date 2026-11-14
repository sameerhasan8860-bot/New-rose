import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Group, GroupSetting, ProcessedUpdate, UpdateClaim


class GroupRepository:
    """Every method requires a chat_id; tenant scope is never inferred."""
    async def ensure_group(self, session: AsyncSession, chat_id: int, title: str = "") -> Group:
        group = await session.get(Group, chat_id)
        if group is None:
            group = Group(chat_id=chat_id, title=title)
            session.add(group)
            await session.flush()
        elif title and group.title != title:
            group.title = title
        return group

    async def get_setting(self, session: AsyncSession, chat_id: int, key: str, default=None):
        row = await session.get(GroupSetting, (chat_id, key))
        return default if row is None else json.loads(row.value_json)

    async def set_setting(self, session: AsyncSession, chat_id: int, key: str, value) -> None:
        await self.ensure_group(session, chat_id)
        row = await session.get(GroupSetting, (chat_id, key))
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if row is None:
            session.add(GroupSetting(chat_id=chat_id, key=key, value_json=encoded))
        else:
            row.value_json = encoded


async def mark_update_processed(session: AsyncSession, update_id: int) -> bool:
    """Return True once; a unique primary key prevents concurrent duplicate processing."""
    bind = session.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(ProcessedUpdate).values(update_id=update_id).on_conflict_do_nothing(index_elements=["update_id"])
    elif dialect == "postgresql":
        statement = pg_insert(ProcessedUpdate).values(update_id=update_id).on_conflict_do_nothing(index_elements=["update_id"])
    else:
        try:
            session.add(ProcessedUpdate(update_id=update_id))
            await session.flush()
            return True
        except IntegrityError:
            await session.rollback()
            return False
    result = await session.execute(statement)
    return result.rowcount == 1



async def claim_update(session: AsyncSession, update_id: int, owner_token: str, lease_seconds: int = 300) -> bool:
    """Atomically acquire an update lease; an unexpired owner's lease cannot be stolen."""
    now = datetime.now(timezone.utc)
    values = {"update_id": update_id, "owner_token": owner_token, "expires_at": now + timedelta(seconds=lease_seconds)}
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(UpdateClaim).values(**values).on_conflict_do_update(
            index_elements=["update_id"],
            set_={"owner_token": owner_token, "expires_at": values["expires_at"]},
            where=UpdateClaim.expires_at < now,
        )
    elif dialect == "postgresql":
        statement = pg_insert(UpdateClaim).values(**values).on_conflict_do_update(
            index_elements=["update_id"],
            set_={"owner_token": owner_token, "expires_at": values["expires_at"]},
            where=UpdateClaim.expires_at < now,
        )
    else:
        raise RuntimeError(f"Atomic update leases are unsupported for database dialect: {dialect}")
    result = await session.execute(statement)
    return result.rowcount == 1


async def release_update_claim(session: AsyncSession, update_id: int, owner_token: str) -> None:
    from sqlalchemy import delete
    await session.execute(delete(UpdateClaim).where(
        UpdateClaim.update_id == update_id,
        UpdateClaim.owner_token == owner_token,
    ))
