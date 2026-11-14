"""Federation membership operations. Every member group must explicitly opt in."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Federation, FederationBan, FederationGroup, Group


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


async def federation_for_group(session, chat_id: int):
    membership = await session.scalar(select(FederationGroup).where(FederationGroup.chat_id == chat_id))
    if membership is None:
        return None
    return await session.get(Federation, membership.federation_id)


async def record_federation_ban(session, *, federation_id: int, user_id: int,
                                actor_chat_id: int, actor_id: int, reason: str = "") -> FederationBan:
    existing = await session.scalar(select(FederationBan).where(
        FederationBan.federation_id == federation_id, FederationBan.user_id == user_id
    ))
    if existing:
        existing.actor_chat_id = actor_chat_id
        existing.actor_id = actor_id
        existing.reason = reason[:1000]
        await session.flush()
        return existing
    row = FederationBan(federation_id=federation_id, user_id=user_id,
                        actor_chat_id=actor_chat_id, actor_id=actor_id, reason=reason[:1000])
    session.add(row)
    await session.flush()
    return row


async def remove_federation_ban(session, *, federation_id: int, user_id: int) -> bool:
    row = await session.scalar(select(FederationBan).where(
        FederationBan.federation_id == federation_id, FederationBan.user_id == user_id
    ))
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def federation_ban_exists(session, *, federation_id: int, user_id: int) -> bool:
    return await session.scalar(select(FederationBan.id).where(
        FederationBan.federation_id == federation_id, FederationBan.user_id == user_id
    )) is not None


async def rename_federation(session, *, federation_id: int, owner_chat_id: int, name: str) -> Federation:
    clean = name.strip().lower()
    if not clean or len(clean) > 64:
        raise ValueError("Federation name must be 1–64 characters.")
    federation = await session.get(Federation, federation_id)
    if federation is None:
        raise ValueError("Federation not found.")
    if federation.owner_chat_id != owner_chat_id:
        raise PermissionError("Only the federation's owner group can rename it.")
    duplicate = await session.scalar(select(Federation).where(
        Federation.name == clean, Federation.id != federation_id
    ))
    if duplicate:
        raise ValueError("That federation name is already in use.")
    federation.name = clean
    await session.flush()
    return federation


async def delete_federation(session, *, federation_id: int, owner_chat_id: int) -> bool:
    federation = await session.get(Federation, federation_id)
    if federation is None:
        return False
    if federation.owner_chat_id != owner_chat_id:
        raise PermissionError("Only the federation's owner group can delete it.")
    await session.delete(federation)
    await session.flush()
    return True
