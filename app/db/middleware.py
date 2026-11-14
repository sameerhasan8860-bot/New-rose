from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from typing import Any, Awaitable, Callable
from app.db.repositories import mark_update_processed


class UpdateDeduplicationMiddleware(BaseMiddleware):
    """Suppress duplicate Telegram update deliveries using durable storage."""
    def __init__(self, database) -> None:
        self.database = database

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)
        async with self.database.sessions() as session:
            async with session.begin():
                first_delivery = await mark_update_processed(session, event.update_id)
        if not first_delivery:
            return None
        return await handler(event, data)
