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
from app.services.captcha import captcha_expiry_worker


async def main() -> None:
    settings = Settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    os.environ["DATABASE_URL"] = settings.database_url
    migration = await asyncio.create_subprocess_exec(sys.executable, "-m", "alembic", "upgrade", "head")
    if await migration.wait() != 0:
        raise RuntimeError("Database migration failed; refusing to start the bot")
    database = Database(settings.database_url)
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    private_commands = [
        BotCommand(command="start", description="Open MASTER X welcome"),
        BotCommand(command="help", description="Browse help and command categories"),
        BotCommand(command="about", description="About MASTER X"),
        BotCommand(command="id", description="Show chat and user IDs"),
        BotCommand(command="ping", description="Check bot response"),
        BotCommand(command="status", description="Check bot status"),
    ]
    group_commands = private_commands + [
        BotCommand(command="settings", description="View group settings status"),
        BotCommand(command="ban", description="Ban a replied-to member"),
        BotCommand(command="tban", description="Temporarily ban a member"),
        BotCommand(command="kick", description="Remove a replied-to member"),
        BotCommand(command="unban", description="Unban a member"),
        BotCommand(command="mute", description="Mute a replied-to member"),
        BotCommand(command="tmute", description="Temporarily mute a member"),
        BotCommand(command="unmute", description="Unmute a member"),
        BotCommand(command="warn", description="Warn a replied-to member"),
        BotCommand(command="warnings", description="View member warnings"),
        BotCommand(command="resetwarnings", description="Reset member warnings"),
        BotCommand(command="purge", description="Delete recent messages"),
        BotCommand(command="antiflood", description="Configure flood protection"),
        BotCommand(command="captcha", description="Configure join CAPTCHA"),
        BotCommand(command="antiraid", description="Configure anti-raid alerts"),
        BotCommand(command="lock", description="Lock a message category"),
        BotCommand(command="unlock", description="Unlock a message category"),
        BotCommand(command="locks", description="List active locks"),
        BotCommand(command="blocklist", description="Manage blocked terms"),
        BotCommand(command="welcome", description="Toggle welcome messages"),
        BotCommand(command="setwelcome", description="Set the welcome template"),
        BotCommand(command="goodbye", description="Toggle goodbye messages"),
        BotCommand(command="filter", description="Add a keyword auto-reply"),
        BotCommand(command="filters", description="List keyword filters"),
        BotCommand(command="stop", description="Remove a keyword filter"),
        BotCommand(command="save", description="Save a group note"),
        BotCommand(command="get", description="Retrieve a group note"),
        BotCommand(command="notes", description="List saved notes"),
        BotCommand(command="report", description="Report a replied-to message"),
        BotCommand(command="reports", description="Review group reports"),
        BotCommand(command="adminlog", description="View moderation history"),
        BotCommand(command="fed", description="Manage federation membership"),
        BotCommand(command="fban", description="Federation-ban a user"),
        BotCommand(command="funban", description="Revoke a federation ban"),
        BotCommand(command="privacy", description="View or erase your records"),
        BotCommand(command="topic", description="Manage forum topics"),
        BotCommand(command="export", description="Export group settings"),
        BotCommand(command="import", description="Import group settings"),
        BotCommand(command="clean", description="Clean recent messages"),
        BotCommand(command="format", description="Format text"),
        BotCommand(command="disable", description="Disable a group command"),
        BotCommand(command="enable", description="Re-enable a group command"),
        BotCommand(command="disabled", description="List disabled commands"),
        BotCommand(command="disableadmin", description="Set disabled-command admin policy"),
    ]
    await bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    dp = Dispatcher()
    dp["database"] = database
    dp["settings"] = settings
    dp.update.outer_middleware(UpdateDeduplicationMiddleware(database))
    dp.include_router(router)
    expiry_task = asyncio.create_task(captcha_expiry_worker(bot, database))
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        expiry_task.cancel()
        try:
            await expiry_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
