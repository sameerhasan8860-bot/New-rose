import asyncio
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
            expired = [(row.id, row.chat_id, row.user_id) for row in rows]
        for challenge_id, chat_id, user_id in expired:
            try:
                chat = await bot.get_chat(chat_id)
                if chat.permissions is None:
                    continue
                await bot.restrict_chat_member(chat_id, user_id, permissions=chat.permissions)
            except (TelegramBadRequest, TelegramForbiddenError):
                continue
            async with database.sessions() as session:
                async with session.begin():
                    row = await session.get(CaptchaChallenge, challenge_id)
                    if row is not None and row.status == "pending":
                        row.status = "expired"
