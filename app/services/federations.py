"""Federation membership operations. Every member group must explicitly opt in."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Federation, FederationGroup, Group


async def create_federation(session, *, name: str, chat_id: int, actor_id: int) -> Federation:
    clean = name.strip().lower()
    if not clean or len(clean) > 64:
        raise ValueError("Federation name must be 1–64 characters.")
    existing = await session.scalar(select(Federation).where(Federation.name == clean))
    if existing:
        raise ValueError("That federation name already exists.")
    group = await session.get(Group, chat_id)
    if group is None:
        group = Group(chat_id=chat_id, title="")
        session.add(group)
        await session.flush()
    federation = Federation(name=clean, owner_chat_id=chat_id, created_by=actor_id)
    session.add(federation)
    await session.flush()
    session.add(FederationGroup(federation_id=federation.id, chat_id=chat_id, consented_by=actor_id))
    await session.flush()
    return federation


async def join_federation(session, *, federation_id: int, chat_id: int, actor_id: int) -> None:
    federation = await session.get(Federation, federation_id)
    if federation is None:
        raise ValueError("Federation not found.")
    current = await session.scalar(select(FederationGroup).where(FederationGroup.chat_id == chat_id))
    if current:
        if current.federation_id == federation_id:
            raise ValueError("This group has already opted in.")
        raise ValueError("This group is already connected to another federation. Leave it first.")
    group = await session.get(Group, chat_id)
    if group is None:
        session.add(Group(chat_id=chat_id, title=""))
        await session.flush()
    session.add(FederationGroup(federation_id=federation_id, chat_id=chat_id, consented_by=actor_id))
    await session.flush()


async def leave_federation(session, *, chat_id: int) -> bool:
    membership = await session.scalar(select(FederationGroup).where(FederationGroup.chat_id == chat_id))
    if membership is None:
        return False
    await session.delete(membership)
    await session.flush()
    return True


async def federation_members(session, federation_id: int) -> list[int]:
    return list((await session.scalars(
        select(FederationGroup.chat_id).where(FederationGroup.federation_id == federation_id).order_by(FederationGroup.consented_at)
    )).all())
