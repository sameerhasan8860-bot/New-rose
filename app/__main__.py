import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import Settings
from app.db.engine import Database
from app.db.middleware import UpdateDeduplicationMiddleware
from app.handlers import router


async def main() -> None:
    settings = Settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    os.environ["DATABASE_URL"] = settings.database_url
    migration = await asyncio.create_subprocess_exec(sys.executable, "-m", "alembic", "upgrade", "head")
    if await migration.wait() != 0:
        raise RuntimeError("Database migration failed; refusing to start the bot")
    database = Database(settings.database_url)
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp["database"] = database
    dp["settings"] = settings
    dp.update.outer_middleware(UpdateDeduplicationMiddleware(database))
    dp.include_router(router)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
