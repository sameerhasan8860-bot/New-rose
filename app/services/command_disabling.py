import json
from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select
from app.db.models import GroupSetting


class CommandDisablingMiddleware(BaseMiddleware):
    """Enforce per-chat disabled commands before command handlers run."""
    CONTROL_COMMANDS = {"disable", "enable", "disabled", "disableadmin"}

    async def __call__(self, handler, event, data):
        if not isinstance(event, Message) or not event.text or event.chat.type not in ("group", "supergroup"):
            return await handler(event, data)
        head = event.text.split(maxsplit=1)[0].split("@", 1)[0]
        if not head.startswith("/"):
            return await handler(event, data)
        command = head[1:].split(":", 1)[0].lower()
        if command in self.CONTROL_COMMANDS:
            return await handler(event, data)
        database = data.get("database")
        if database is None:
            return await handler(event, data)
        async with database.sessions() as session:
            rows = (await session.scalars(select(GroupSetting).where(
                GroupSetting.chat_id == event.chat.id,
                GroupSetting.key.in_(["disabled_commands", "disable_commands_for_admins"]),
            ))).all()
        settings = {row.key: json.loads(row.value_json) for row in rows}
        disabled = set(settings.get("disabled_commands", []))
        if command not in disabled:
            return await handler(event, data)
        is_admin = False
        if event.from_user and not event.from_user.is_bot:
            try:
                from app.services.authorization import has_group_admin_rights
                is_admin = await has_group_admin_rights(data["bot"], event.chat.id, event.from_user.id)
            except Exception:
                is_admin = False
        if is_admin and not settings.get("disable_commands_for_admins", False):
            return await handler(event, data)
        await event.answer(f"⛔ /{command} is disabled in this group.")
        return None
