import uuid
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from typing import Any, Awaitable, Callable
from app.db.repositories import claim_update, mark_update_processed, release_update_claim
from app.db.models import ProcessedUpdate


class UpdateDeduplicationMiddleware(BaseMiddleware):
    """Claim each update atomically, then commit completion only after handler success."""
    def __init__(self, database, lease_seconds: int = 300) -> None:
        self.database = database
        self.lease_seconds = lease_seconds

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)
        token = uuid.uuid4().hex
        async with self.database.sessions() as session:
            async with session.begin():
                if await session.get(ProcessedUpdate, event.update_id) is not None:
                    return None
                acquired = await claim_update(session, event.update_id, token, self.lease_seconds)
        if not acquired:
            return None
        try:
            result = await handler(event, data)
            async with self.database.sessions() as session:
                async with session.begin():
                    await mark_update_processed(session, event.update_id)
                    await release_update_claim(session, event.update_id, token)
            return result
        except BaseException:
            async with self.database.sessions() as session:
                async with session.begin():
                    await release_update_claim(session, event.update_id, token)
            raise
