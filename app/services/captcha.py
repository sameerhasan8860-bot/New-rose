import asyncio
import json
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import select

from app.db.engine import Database
from app.db.models import CaptchaChallenge


async def captcha_expiry_worker(bot: Bot, database: Database) -> None:
    """Restore expired CAPTCHA members to group defaults; retry transient API failures."""
    while True:
        await asyncio.sleep(30)
        now = datetime.now(timezone.utc)
        async with database.sessions() as session:
            rows = (await session.scalars(
                select(CaptchaChallenge).where(
                    CaptchaChallenge.status == "pending",
                    CaptchaChallenge.expires_at < now,
                ).limit(100)
            )).all()
            expired = [(row.id, row.chat_id, row.user_id, row.previous_permissions_json) for row in rows]
        for challenge_id, chat_id, user_id, previous_permissions_json in expired:
            try:
                chat = await bot.get_chat(chat_id)
                permissions = json.loads(previous_permissions_json) if previous_permissions_json else (chat.permissions.model_dump(exclude_none=True) if chat.permissions else None)
                if permissions is None:
                    continue
                from aiogram.types import ChatPermissions
                await bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(**permissions))
            except (TelegramBadRequest, TelegramForbiddenError):
                continue
            async with database.sessions() as session:
                async with session.begin():
                    row = await session.get(CaptchaChallenge, challenge_id)
                    if row is not None and row.status == "pending":
                        row.status = "expired"
