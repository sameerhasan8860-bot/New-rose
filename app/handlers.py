import re
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message, User
from sqlalchemy import func, select

from app.db.engine import Database
from app.db.models import Group, ModerationAction, WarningRecord
from app.services.authorization import has_group_admin_rights

router = Router(name="core")
BRAND = "✦ 𝗠𝗔𝗦𝗧𝗘𝗥 𝗫 ✦"
GROUP_TYPES = (ChatType.GROUP, ChatType.SUPERGROUP)
_DURATION = re.compile(r"^(\d+)([smhd])$", re.IGNORECASE)


def _args(message: Message) -> str:
    parts = (message.text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _parse_duration(value: str):
    match = _DURATION.fullmatch(value)
    if not match:
        return None
    amount = int(match.group(1))
    if amount <= 0:
        return None
    delta = {
        "s": timedelta(seconds=amount),
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
    }[match.group(2).lower()]
    return delta if delta <= timedelta(days=366) else None


async def _moderation_context(message: Message, bot: Bot, *, require_bot_restrict: bool = True, allow_user_id: bool = False):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("This command works inside a group only.")
        return None
    actor = message.from_user
    if actor is None or not await has_group_admin_rights(bot, message.chat.id, actor.id):
        await message.answer("⛔ Only current group administrators can use this command.")
        return None
    try:
        actor_member = await bot.get_chat_member(message.chat.id, actor.id)
        if require_bot_restrict and actor_member.status != ChatMemberStatus.CREATOR and not getattr(actor_member, "can_restrict_members", False):
            await message.answer("⛔ You need the Telegram 'Ban users' admin permission.")
            return None

        target = message.reply_to_message.from_user if message.reply_to_message else None
        if target is None and allow_user_id:
            raw_id = _args(message).split(maxsplit=1)[0] if _args(message) else ""
            if not raw_id.isdigit():
                await message.answer("Usage: /unban USER_ID, or reply to a user's message with /unban.")
                return None
            target = User(id=int(raw_id), is_bot=False, first_name=f"User {raw_id}")
        if target is None:
            await message.answer("Reply to the target user's message.")
            return None
        if target.is_bot or target.id == actor.id:
            await message.answer("⛔ This target cannot be moderated.")
            return None

        # A banned user cannot reliably be resolved as a current group member.
        if not allow_user_id or message.reply_to_message is not None:
            target_member = await bot.get_chat_member(message.chat.id, target.id)
            if target_member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                await message.answer("⛔ Moderation actions cannot target group administrators.")
                return None

        if require_bot_restrict:
            me = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
            if me.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR) or not getattr(me, "can_restrict_members", False):
                await message.answer("I need the group's 'Ban users' permission.")
                return None
        return actor, target
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.answer(f"Telegram could not verify permissions or target: {str(exc)[:180]}")
        return None


async def _record_action(database: Database, chat_id: int, title: str, actor_id: int, target_id: int, action: str, reason: str = ""):
    async with database.sessions() as session:
        async with session.begin():
            group = await session.get(Group, chat_id)
            if group is None:
                session.add(Group(chat_id=chat_id, title=title or ""))
                await session.flush()
            session.add(ModerationAction(chat_id=chat_id, actor_id=actor_id, target_id=target_id, action=action, reason=reason[:1000]))


@router.message(Command("start"))
async def start(message: Message):
    await message.answer(f"{BRAND}\n━━━━━━━━━━━━━━━━━━\nYour community command center is coming online.\n\n🛡️ Moderation • ✨ Automation\n🤖 AI companion • 📊 Community insights\n\nUse /help to explore this build.")


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        f"{BRAND}\n𝗖𝗢𝗥𝗘 & 𝗠𝗢𝗗𝗘𝗥𝗔𝗧𝗜𝗢𝗡\n/start — Welcome\n/help — Commands\n/settings — Group settings status\n/about — About MASTER X\n/id — IDs\n/ping — Runtime response\n/status — Health\n\n"
        "Reply to a member: /ban, /kick, /mute 10m [reason], /unmute, /warn [reason], /warnings.\n"
        "/unban accepts a replied user or numeric Telegram USER_ID. Admin rights and bot permissions are checked."
    )


@router.message(Command("settings"))
async def settings_command(message: Message, bot: Bot):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("⚙️ Group settings are available inside a group.")
        return
    if not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can access group settings.")
        return
    await message.answer("⚙️ 𝗚𝗥𝗢𝗨𝗣 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦\nGroup isolation is enabled. Interactive settings are still under development; no settings were changed.")


@router.message(Command("about"))
async def about(message: Message):
    await message.answer(f"{BRAND}\nA modular community-management platform. Independent from Rose, Group Help, Iris, and Combot.")


@router.message(Command("id"))
async def ids(message: Message):
    user_id = message.from_user.id if message.from_user else "unknown"
    await message.answer(f"🆔 Chat ID: <code>{message.chat.id}</code>\nUser ID: <code>{user_id}</code>")


@router.message(Command("ping"))
async def ping(message: Message):
    await message.answer("🏓 Pong — MASTER X is responding.")


@router.message(Command("status"))
async def status(message: Message):
    await message.answer("🟢 MASTER X process is online. Phase 3 moderation handlers are loaded.")


async def _apply_restriction(message: Message, bot: Bot, database: Database, action: str, *, until_date=None, reason=""):
    context = await _moderation_context(message, bot, allow_user_id=(action == "unban"))
    if not context:
        return
    actor, target = context
    try:
        if action in ("ban", "kick"):
            await bot.ban_chat_member(message.chat.id, target.id)
            if action == "kick":
                await bot.unban_chat_member(message.chat.id, target.id, only_if_banned=True)
        elif action == "unban":
            await bot.unban_chat_member(message.chat.id, target.id, only_if_banned=True)
        elif action == "mute":
            await bot.restrict_chat_member(
                message.chat.id, target.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
        elif action == "unmute":
            chat = await bot.get_chat(message.chat.id)
            defaults = chat.permissions or ChatPermissions()
            await bot.restrict_chat_member(message.chat.id, target.id, permissions=defaults)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.answer(f"Telegram rejected the action: {str(exc)[:250]}")
        return

    try:
        await _record_action(database, message.chat.id, message.chat.title or "", actor.id, target.id, action, reason)
    except Exception:
        # Do not hide a successful Telegram action if audit persistence fails.
        await message.answer("⚠️ Telegram action succeeded, but saving its audit record failed. Check the database.")
        return
    await message.answer(
        f"✅ {action.title()} applied to <a href='tg://user?id={target.id}'>{target.full_name}</a>."
        + (f"\nReason: {reason[:500]}" if reason else "")
    )


@router.message(Command("ban"))
async def ban(message: Message, bot: Bot, database: Database):
    await _apply_restriction(message, bot, database, "ban", reason=_args(message))


@router.message(Command("kick"))
async def kick(message: Message, bot: Bot, database: Database):
    await _apply_restriction(message, bot, database, "kick", reason=_args(message))


@router.message(Command("unban"))
async def unban(message: Message, bot: Bot, database: Database):
    await _apply_restriction(message, bot, database, "unban", reason=_args(message))


@router.message(Command("mute"))
async def mute(message: Message, bot: Bot, database: Database):
    parts = _args(message).split(maxsplit=1)
    duration = _parse_duration(parts[0]) if parts else None
    if duration is None:
        await message.answer("Usage: reply to a member with /mute 10m [reason]. Units: s, m, h, d; maximum 366 days.")
        return
    reason = parts[1] if len(parts) > 1 else ""
    await _apply_restriction(message, bot, database, "mute", until_date=datetime.now(timezone.utc) + duration, reason=reason)


@router.message(Command("unmute"))
async def unmute(message: Message, bot: Bot, database: Database):
    await _apply_restriction(message, bot, database, "unmute", reason=_args(message))


@router.message(Command("warn"))
async def warn(message: Message, bot: Bot, database: Database):
    context = await _moderation_context(message, bot, require_bot_restrict=False)
    if not context:
        return
    actor, target = context
    reason = _args(message) or "No reason provided"
    async with database.sessions() as session:
        async with session.begin():
            group = await session.get(Group, message.chat.id)
            if group is None:
                session.add(Group(chat_id=message.chat.id, title=message.chat.title or ""))
                await session.flush()
            session.add(WarningRecord(chat_id=message.chat.id, user_id=target.id, actor_id=actor.id, reason=reason[:1000]))
            session.add(ModerationAction(chat_id=message.chat.id, actor_id=actor.id, target_id=target.id, action="warn", reason=reason[:1000]))
            count = await session.scalar(
                select(func.count()).select_from(WarningRecord).where(
                    WarningRecord.chat_id == message.chat.id, WarningRecord.user_id == target.id
                )
            )
    await message.answer(f"⚠️ Warning recorded for <a href='tg://user?id={target.id}'>{target.full_name}</a>. Total warnings in this group: {count}.")


@router.message(Command("warnings"))
async def warnings(message: Message, bot: Bot, database: Database):
    context = await _moderation_context(message, bot, require_bot_restrict=False)
    if not context:
        return
    _, target = context
    async with database.sessions() as session:
        count = await session.scalar(
            select(func.count()).select_from(WarningRecord).where(
                WarningRecord.chat_id == message.chat.id, WarningRecord.user_id == target.id
            )
        )
        rows = (await session.scalars(
            select(WarningRecord).where(
                WarningRecord.chat_id == message.chat.id, WarningRecord.user_id == target.id
            ).order_by(WarningRecord.created_at.desc()).limit(10)
        )).all()
    if not rows:
        await message.answer(f"✅ {target.full_name} has no warnings in this group.")
        return
    details = "\n".join(f"• {row.reason[:120]}" for row in rows)
    await message.answer(f"⚠️ <b>{target.full_name}</b> — {count} warning(s) in this group\n{details}")
