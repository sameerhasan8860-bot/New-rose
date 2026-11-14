"""Cross-worker antiraid event counting and one-time threshold alert claims."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import Group, RaidAlert, RaidJoinEvent


async def record_join_and_claim_alert(session, *, chat_id: int, user_id: int, now: datetime | None = None) -> bool:
    """Record a join and atomically claim the fifth-join alert for this rolling 30s window."""
    now = now or datetime.now(timezone.utc)
    group = await session.get(Group, chat_id)
    if group is None:
        session.add(Group(chat_id=chat_id, title=""))
        await session.flush()
    event = RaidJoinEvent(chat_id=chat_id, user_id=user_id, joined_at=now)
    session.add(event)
    await session.flush()
    recent = (await session.scalars(
        select(RaidJoinEvent)
        .where(RaidJoinEvent.chat_id == chat_id, RaidJoinEvent.joined_at >= now - timedelta(seconds=30))
        .order_by(RaidJoinEvent.joined_at, RaidJoinEvent.id)
        .limit(5)
    )).all()
    if len(recent) < 5:
        return False
    threshold_id = recent[4].id
    values = {"chat_id": chat_id, "threshold_event_id": threshold_id, "created_at": now}
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(RaidAlert).values(**values).on_conflict_do_nothing(
            index_elements=["chat_id", "threshold_event_id"]
        )
    elif dialect == "postgresql":
        statement = pg_insert(RaidAlert).values(**values).on_conflict_do_nothing(
            index_elements=["chat_id", "threshold_event_id"]
        )
    else:
        raise RuntimeError(f"Atomic antiraid alert claims unsupported for database dialect: {dialect}")
    result = await session.execute(statement)
    return result.rowcount == 1
