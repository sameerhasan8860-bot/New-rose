import re
from datetime import datetime, timedelta, timezone
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import select, func
from app.services.authorization import has_group_admin_rights
from app.db.engine import Database
from app.db.models import Group, ModerationAction, WarningRecord

router = Router(name="core")
BRAND = "✦ 𝗠𝗔𝗦𝗧𝗘𝗥 𝗫 ✦"
GROUP_TYPES = (ChatType.GROUP, ChatType.SUPERGROUP)

async def _moderation_context(message: Message, bot: Bot):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("This command works inside a group only.")
        return None
    actor = message.from_user
    if actor is None or not await has_group_admin_rights(bot, message.chat.id, actor.id):
        await message.answer("⛔ Only group administrators can use this command.")
        return None
    actor_member = await bot.get_chat_member(message.chat.id, actor.id)
    if actor_member.status != ChatMemberStatus.CREATOR and not getattr(actor_member, "can_restrict_members", False):
        await message.answer("⛔ You need the Telegram 'Ban users' admin permission to moderate members.")
        return None
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer("Reply to the target user's message, then run this command.")
        return None
    target = message.reply_to_message.from_user
    if target.is_bot:
        await message.answer("Bot accounts cannot be moderated with this command.")
        return None
    if target.id == actor.id:
        await message.answer("You cannot use this command on yourself.")
        return None
    try:
        target_member = await bot.get_chat_member(message.chat.id, target.id)
    except (TelegramBadRequest, TelegramForbiddenError):
        await message.answer("I could not verify the target user's membership.")
        return None
    if target_member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
        await message.answer("⛔ Moderation actions cannot target group administrators.")
        return None
    try:
        me = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
    except (TelegramBadRequest, TelegramForbiddenError):
        await message.answer("I could not verify my own permissions.")
        return None
    if me.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR) or not getattr(me, "can_restrict_members", False):
        await message.answer("I need the group's 'Ban users' permission to do that.")
        return None
    return actor, target

async def _record_action(database: Database, chat_id: int, title: str, actor_id: int, target_id: int, action: str, reason: str = ""):
    async with database.sessions() as session:
        async with session.begin():
            group = await session.get(Group, chat_id)
            if group is None:
                session.add(Group(chat_id=chat_id, title=title or ""))
                await session.flush()
            session.add(ModerationAction(chat_id=chat_id, actor_id=actor_id, target_id=target_id, action=action, reason=reason[:1000]))

def _args(message: Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

_DURATION = re.compile(r"^(\d+)([smhd])$", re.IGNORECASE)
def _parse_duration(value: str):
    match = _DURATION.fullmatch(value)
    if not match:
        return None
    amount = int(match.group(1))
    if amount <= 0:
        return None
    unit = match.group(2).lower()
    delta = {"s": timedelta(seconds=amount), "m": timedelta(minutes=amount), "h": timedelta(hours=amount), "d": timedelta(days=amount)}[unit]
    if delta > timedelta(days=366):
        return None
    return delta

@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(f"{BRAND}\\n━━━━━━━━━━━━━━━━━━\\nYour community command center is coming online.\\n\\n🛡️ Moderation  •  ✨ Automation\\n🤖 AI companion • 📊 Community insights\\n\\nUse /help to explore the commands available in this build.\\n━━━━━━━━━━━━━━━━━━")

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(f"{BRAND}\\n𝗖𝗢𝗥𝗘 & 𝗠𝗢𝗗𝗘𝗥𝗔𝗧𝗜𝗢𝗡\\n/start — Welcome\\n/help — Available commands\\n/settings — Group settings status (admins)\\n/about — About MASTER X\\n/id — Chat and user IDs\\n/ping — Runtime response\\n/status — Basic health\\n\\nReply to a user's message: /ban, /unban, /kick, /mute [10m|1h|1d], /unmute, /warn [reason], /warnings.\\nOnly verified group admins can moderate; the bot needs Ban users permission.")

@router.message(Command("settings"))
async def settings_command(message: Message, bot: Bot) -> None:
    if message.chat.type not in GROUP_TYPES:
        await message.answer("⚙️ Group settings are available inside a group, for its administrators.")
        return
    if not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can access group settings.")
        return
    await message.answer("⚙️ 𝗚𝗥𝗢𝗨𝗣 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦\\nYour group is isolated from every other group.\\nThe interactive settings dashboard is still under development; no settings have been changed.")

@router.message(Command("about"))
async def about(message: Message) -> None:
    await message.answer(f"{BRAND}\\nA modular community-management platform.\\nIndependent project; not affiliated with Rose, Group Help, Iris, or Combot.")

@router.message(Command("id"))
async def ids(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else "unknown"
    await message.answer(f"🆔 Chat ID: <code>{message.chat.id}</code>\\nUser ID: <code>{user_id}</code>")

@router.message(Command("ping"))
async def ping(message: Message) -> None:
    await message.answer("🏓 Pong — MASTER X is responding.")

@router.message(Command("status"))
async def status(message: Message) -> None:
    await message.answer("🟢 Process is online. Phase 3 moderation commands are enabled.")

async def _apply_restriction(message: Message, bot: Bot, database: Database, action: str, until_date=None, reason=""):
    context = await _moderation_context(message, bot)
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
            await bot.restrict_chat_member(message.chat.id, target.id, permissions=ChatPermissions(can_send_messages=False), until_date=until_date)
        elif action == "unmute":
            await bot.restrict_chat_member(message.chat.id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True))
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.answer(f"Telegram rejected the action: {str(exc)[:250]}")
        return
    await _record_action(database, message.chat.id, message.chat.title or "", actor.id, target.id, action, reason)
    await message.answer(f"✅ {action.title()} applied to <a href='tg://user?id={target.id}'>{target.full_name}</a>." + (f"\\nReason: {reason}" if reason else ""))

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
    args = _args(message)
    pieces = args.split(maxsplit=1)
    duration = _parse_duration(pieces[0]) if pieces else None
    if not duration:
        await message.answer("Usage: reply with /mute 10m [reason] (s, m, h, d; maximum 366 days).")
        return
    reason = pieces[1] if len(pieces) > 1 else ""
    await _apply_restriction(message, bot, database, "mute", datetime.now(timezone.utc) + duration, reason)

@router.message(Command("unmute"))
async def unmute(message: Message, bot: Bot, database: Database):
    await _apply_restriction(message, bot, database, "unmute", reason=_args(message))

@router.message(Command("warn"))
async def warn(message: Message, bot: Bot, database: Database):
    context = await _moderation_context(message, bot)
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
            count = await session.scalar(select(func.count()).select_from(WarningRecord).where(WarningRecord.chat_id == message.chat.id, WarningRecord.user_id == target.id))
    await message.answer(f"⚠️ Warning recorded for <a href='tg://user?id={target.id}'>{target.full_name}</a>. Total warnings in this group: {count}.")

@router.message(Command("warnings"))
async def warnings(message: Message, bot: Bot, database: Database):
    context = await _moderation_context(message, bot)
    if not context:
        return
    _, target = context
    async with database.sessions() as session:
        count = await session.scalar(select(func.count()).select_from(WarningRecord).where(WarningRecord.chat_id == message.chat.id, WarningRecord.user_id == target.id))
        rows = (await session.scalars(select(WarningRecord).where(WarningRecord.chat_id == message.chat.id, WarningRecord.user_id == target.id).order_by(WarningRecord.created_at.desc()).limit(10))).all()
    if not rows:
        await message.answer(f"✅ {target.full_name} has no warnings in this group.")
        return
    details = "\\n".join(f"• {row.reason[:120]}" for row in rows)
    await message.answer(f"⚠️ <b>{target.full_name}</b> — {count} warning(s) in this group\\n{details}")
