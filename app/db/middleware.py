from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from typing import Any, Awaitable, Callable
from app.db.repositories import mark_update_processed


class UpdateDeduplicationMiddleware(BaseMiddleware):
    """Persist a delivery only after its handler succeeds, so failed handlers can retry.

    The post-handler commit avoids permanently dropping an update after a handler
    exception. Concurrent duplicate deliveries still require a lease/claim table
    before this can provide strict exactly-once processing.
    """
    def __init__(self, database) -> None:
        self.database = database

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)
        async with self.database.sessions() as session:
            existing = await session.get(__import__("app.db.models", fromlist=["ProcessedUpdate"]).ProcessedUpdate, event.update_id)
        if existing is not None:
            return None
        result = await handler(event, data)
        async with self.database.sessions() as session:
            async with session.begin():
                await mark_update_processed(session, event.update_id)
        return result
