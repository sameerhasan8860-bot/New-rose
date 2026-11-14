import json
import random
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatMemberUpdated, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Message, User
from sqlalchemy import func, select, update

from app.db.engine import Database
from app.db.models import BlockedTerm, CaptchaChallenge, Group, GroupFilter, GroupSetting, ModerationAction, Note, ReportRecord, WarningRecord
from app.db.repositories import GroupRepository
from app.services.authorization import has_group_admin_rights

router = Router(name="core")


def _allow_human_message(message: Message) -> bool:
    """Fail closed for bot-authored updates and anonymous sender identities.

    MASTER X intentionally keeps bot-to-bot command execution disabled until an
    explicit review/approval workflow exists. Anonymous-admin support is also
    fail-closed here rather than trusting sender_chat as a human identity.
    """
    return message.from_user is not None and not message.from_user.is_bot


def _allow_human_callback(callback: CallbackQuery) -> bool:
    return not callback.from_user.is_bot


router.message.filter(_allow_human_message)
router.callback_query.filter(_allow_human_callback)
from app.services.command_disabling import CommandDisablingMiddleware
router.message.middleware(CommandDisablingMiddleware())
_JOIN_WINDOWS = defaultdict(deque)
_FLOOD_WINDOWS = defaultdict(deque)
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
    if actor is None or actor.is_bot or not await has_group_admin_rights(bot, message.chat.id, actor.id):
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


HELP_PAGES = {
    "core": ("✨ 𝗚𝗘𝗡𝗘𝗥𝗔𝗟", "/start — Welcome screen\n/help — Command guide\n/about — About MASTER X\n/id — Show chat and user IDs\n/ping — Check response\n/status — Basic runtime status\n/settings — Group settings status (admins)"),
    "moderation": ("🛡️ 𝗠𝗢𝗗𝗘𝗥𝗔𝗧𝗜𝗢𝗡", "/ban — Ban a replied-to member\n/tban 10m [reason] — Temporary ban\n/kick — Remove a replied-to member\n/unban — Unban replied user or USER_ID\n/mute 10m [reason] — Temporary mute\n/tmute 10m [reason] — Timed mute\n/unmute — Restore group defaults\n/warn [reason] — Warn a member\n/warnings — View member warnings\n/resetwarnings — Reset warnings (reply)\n/purge COUNT — Delete up to 100 messages"),
    "antispam": ("🚨 𝗔𝗡𝗧𝗜-𝗦𝗣𝗔𝗠 & 𝗦𝗔𝗙𝗘𝗧𝗬", "/antiflood on|off — Text flood protection\n/captcha on|off — New-member verification\n/antiraid on|off — Join-spike alerts\n/lock CATEGORY — Lock links/media etc.\n/unlock CATEGORY — Remove a lock\n/locks — List active locks\n/blocklist add|del WORD — Manage blocked terms"),
    "community": ("👋 𝗖𝗢𝗠𝗠𝗨𝗡𝗜𝗧𝗬", "/welcome on|off — Welcome messages\n/setwelcome TEXT — Set welcome template\n/goodbye on|off — Leave notices\n/filter keyword => response — Add auto-reply\n/stop KEYWORD — Remove a filter\n/filters — List filters"),
    "notes": ("🗂️ 𝗡𝗢𝗧𝗘𝗦 & 𝗥𝗘𝗣𝗢𝗥𝗧𝗦", "/save NAME — Save replied-to message\n/get NAME — Retrieve a note\n/notes — List notes\n/report — Report a replied-to message\n/reports — Review reports (admins)\n/closereport ID — Close a report\n/adminlog — Recent moderation log"),
    "federation": ("🌐 𝗙𝗘𝗗𝗘𝗥𝗔𝗧𝗜𝗢𝗡 & 𝗣𝗥𝗜𝗩𝗔𝗖𝗬", "/fed create NAME — Create federation\n/fed join ID — Join federation\n/fed leave — Leave federation\n/fed info — Federation details\n/fban USER_ID [reason] — Federation ban\n/funban USER_ID — Revoke federation ban\n/privacy — Explain stored data\n/privacy delete — Erase your records in this group"),
    "tools": ("⚙️ 𝗧𝗢𝗢𝗟𝗦", "/topic create|close|reopen|delete — Manage forum topics\n/export — Export supported group settings\n/import — Import a settings export\n/clean COUNT — Clean up to 20 recent messages\n/format bold|italic|code|quote TEXT — Format text"),
    "admin": ("🔧 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗡𝗧𝗥𝗢𝗟𝗦", "/disable COMMAND — Disable a command in this group\n/enable COMMAND — Re-enable a command\n/disabled — List disabled commands\n/disableadmin on|off — Apply disabled commands to admins"),
}
HELP_HOME = (
    f"{BRAND}\n━━━━━━━━━━━━━━━━━━━━\n"
    "𝗛𝗘𝗟𝗣 𝗖𝗘𝗡𝗧𝗘𝗥  •  𝗖𝗢𝗠𝗠𝗔𝗡𝗗 𝗚𝗨𝗜𝗗𝗘\n\n"
    "Explore MASTER X tools by category. Select a section below to view commands and usage.\n\n"
    "🛡️ Moderation  ·  🚨 Anti-Spam  ·  👋 Community\n"
    "🗂️ Notes & Reports  ·  🌐 Federation  ·  ⚙️ Tools"
)
HELP_BUTTONS = [
    [("✨ General", "mxhelp:core"), ("🛡️ Moderation", "mxhelp:moderation")],
    [("🚨 Anti-Spam", "mxhelp:antispam"), ("👋 Community", "mxhelp:community")],
    [("🗂️ Notes & Reports", "mxhelp:notes"), ("🌐 Federation", "mxhelp:federation")],
    [("⚙️ Tools", "mxhelp:tools"), ("🔧 Admin", "mxhelp:admin")],
]
def _help_keyboard(page: str = "home") -> InlineKeyboardMarkup:
    style_by_page = {"core": "primary", "moderation": "danger", "antispam": "danger", "community": "success", "notes": "primary", "federation": "primary", "tools": "success", "admin": "primary"}
    rows = [[InlineKeyboardButton(text=label, callback_data=data, style=style_by_page.get(data.split(":")[-1], "primary")) for label, data in row] for row in HELP_BUTTONS]
    if page != "home":
        rows.append([InlineKeyboardButton(text="⬅️ Back to Help", callback_data="mxhelp:home", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("start"))
async def start(message: Message):
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━━━━━\n"
        "𝗬𝗢𝗨𝗥 𝗖𝗢𝗠𝗠𝗨𝗡𝗜𝗧𝗬. 𝗬𝗢𝗨𝗥 𝗖𝗢𝗡𝗧𝗥𝗢𝗟.\n\n"
        "Welcome to MASTER X — your community management companion.\n\n"
        "🛡️ Smart moderation & member safety\n"
        "🚨 Anti-spam, CAPTCHA & anti-raid tools\n"
        "👋 Welcome messages, notes & filters\n"
        "🌐 Federations, reports & privacy controls\n\n"
        "Add me to your group and grant only the permissions needed for the tools you use.\n"
        "Tap Help to explore the command center."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚  Help & Commands", callback_data="mxhelp:home", style="primary")],
        [InlineKeyboardButton(text="ℹ️  About MASTER X", callback_data="mxhelp:about", style="success")],
    ])
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(HELP_HOME, reply_markup=_help_keyboard())


@router.callback_query(F.data.startswith("mxhelp:"))
async def help_navigation(callback: CallbackQuery):
    page = callback.data.split(":", 1)[1]
    if page == "about":
        text = (
            f"{BRAND}\n𝗔𝗕𝗢𝗨𝗧 𝗠𝗔𝗦𝗧𝗘𝗥 𝗫\n\n"
            "A modular community-management bot built for safer, better-organized Telegram groups.\n\n"
            "Use /help to browse the command guide."
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Open Help Center", callback_data="mxhelp:home", style="primary")]
        ])
    elif page == "home":
        text, keyboard = HELP_HOME, _help_keyboard()
    elif page in HELP_PAGES:
        title, body = HELP_PAGES[page]
        text = f"{BRAND}\n━━━━━━━━━━━━━━━━━━━━\n{title}\n\n{body}\n\n<i>Some commands require group-admin rights and matching bot permissions. Use commands in the group where you manage members.</i>"
        keyboard = _help_keyboard(page)
    else:
        await callback.answer("This help section is unavailable.", show_alert=True)
        return
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise
    await callback.answer()


@router.message(Command("disable"))
async def disable_command(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can disable commands.")
        return
    name = _args(message).strip().lstrip("/").split("@", 1)[0].lower()
    from app.services.command_registry import get_command
    if not name or name in {"start", "help", "disable", "enable", "disabled", "disableadmin"} or get_command(name) is None:
        await message.answer("Usage: /disable COMMAND. Only implemented commands can be disabled; control commands stay available.")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            current = await repo.get_setting(session, message.chat.id, "disabled_commands", [])
            if name not in current:
                current.append(name)
            await repo.set_setting(session, message.chat.id, "disabled_commands", sorted(set(current)))
    await message.answer(f"✅ /{name} disabled in this group. Administrators can still use it unless /disableadmin on is set.")


@router.message(Command("enable"))
async def enable_command(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can enable commands.")
        return
    name = _args(message).strip().lstrip("/").split("@", 1)[0].lower()
    if not name:
        await message.answer("Usage: /enable COMMAND")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            current = await repo.get_setting(session, message.chat.id, "disabled_commands", [])
            if name in current:
                current.remove(name)
            await repo.set_setting(session, message.chat.id, "disabled_commands", current)
    await message.answer(f"✅ /{name} enabled in this group.")


@router.message(Command("disabled"))
async def list_disabled_commands(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can view disabled commands.")
        return
    async with database.sessions() as session:
        disabled = await GroupRepository().get_setting(session, message.chat.id, "disabled_commands", [])
    await message.answer("Disabled commands: " + (", ".join("/" + item for item in disabled) if disabled else "none"))


@router.message(Command("disableadmin"))
async def disable_for_admins(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can change this setting.")
        return
    value = _args(message).lower()
    if value not in {"on", "off"}:
        await message.answer("Usage: /disableadmin on|off. When on, disabled commands are blocked for admins too.")
        return
    async with database.sessions() as session:
        async with session.begin():
            await GroupRepository().set_setting(session, message.chat.id, "disable_commands_for_admins", value == "on")
    await message.answer("✅ Disabled commands now apply to admins too." if value == "on" else "✅ Administrators can bypass disabled commands.")


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
            await bot.ban_chat_member(message.chat.id, target.id, until_date=until_date)
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
            if chat.permissions is None:
                await message.answer("I cannot safely determine this group's default permissions, so I did not unmute the member.")
                return
            await bot.restrict_chat_member(message.chat.id, target.id, permissions=chat.permissions)
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


@router.message(Command("tban"))
async def timed_ban(message: Message, bot: Bot, database: Database):
    parts = _args(message).split(maxsplit=1)
    duration = _parse_duration(parts[0]) if parts else None
    if duration is None:
        await message.answer("Usage: reply to a member with /tban 10m [reason]. Units: s, m, h, d; maximum 366 days.")
        return
    reason = parts[1] if len(parts) > 1 else ""
    await _apply_restriction(message, bot, database, "ban",
                             until_date=datetime.now(timezone.utc) + duration, reason=reason)


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


@router.message(Command("tmute"))
async def timed_mute(message: Message, bot: Bot, database: Database):
    parts = _args(message).split(maxsplit=1)
    duration = _parse_duration(parts[0]) if parts else None
    if duration is None:
        await message.answer("Usage: reply to a member with /tmute 10m [reason]. Units: s, m, h, d; maximum 366 days.")
        return
    reason = parts[1] if len(parts) > 1 else ""
    await _apply_restriction(message, bot, database, "mute",
                             until_date=datetime.now(timezone.utc) + duration, reason=reason)


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


@router.message(Command("report"))
async def report_message(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("Use /report as a reply inside the group.")
        return
    reporter = message.from_user
    target_message = message.reply_to_message
    if reporter is None or target_message is None or target_message.from_user is None:
        await message.answer("Reply to the message you want to report, then send /report [reason].")
        return
    target = target_message.from_user
    if target.is_bot or target.id == reporter.id:
        await message.answer("That message cannot be reported.")
        return
    reason = _args(message)[:1000] or "No reason provided"
    async with database.sessions() as session:
        async with session.begin():
            group = await session.get(Group, message.chat.id)
            if group is None:
                session.add(Group(chat_id=message.chat.id, title=message.chat.title or ""))
                await session.flush()
            record = ReportRecord(
                chat_id=message.chat.id, reporter_id=reporter.id, target_id=target.id,
                message_id=target_message.message_id, reason=reason, status="open",
            )
            session.add(record)
            await session.flush()
            report_id = record.id
    notified = 0
    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        for admin in admins:
            if admin.user.is_bot:
                continue
            try:
                await bot.send_message(
                    admin.user.id,
                    f"🚩 <b>Group report #{report_id}</b>\nGroup: {message.chat.title or message.chat.id}\n"
                    f"Reporter: <code>{reporter.id}</code>\nReported user: <code>{target.id}</code>\n"
                    f"Reason: {reason[:500]}",
                )
                notified += 1
            except (TelegramBadRequest, TelegramForbiddenError):
                continue
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    await message.answer(f"🚩 Report #{report_id} saved for this group. Notified {notified} admin(s).")


@router.message(Command("reports"))
async def list_reports(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can review reports in their group.")
        return
    async with database.sessions() as session:
        rows = (await session.scalars(
            select(ReportRecord).where(
                ReportRecord.chat_id == message.chat.id, ReportRecord.status == "open"
            ).order_by(ReportRecord.created_at.desc()).limit(10)
        )).all()
    if not rows:
        await message.answer("✅ There are no open reports in this group.")
        return
    lines = [
        f"#{row.id} · user <code>{row.target_id}</code> · reporter <code>{row.reporter_id}</code>\n"
        f"Message <code>{row.message_id}</code> · {row.reason[:140]}"
        for row in rows
    ]
    await message.answer("🚩 <b>Open reports — this group</b>\n" + "\n\n".join(lines))


@router.message(Command("adminlog"))
async def admin_log(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can view this group's admin log.")
        return
    async with database.sessions() as session:
        rows = (await session.scalars(
            select(ModerationAction).where(ModerationAction.chat_id == message.chat.id)
            .order_by(ModerationAction.created_at.desc()).limit(10)
        )).all()
    if not rows:
        await message.answer("No moderation actions have been recorded in this group yet.")
        return
    lines = [
        f"#{row.id} · <b>{row.action}</b> · actor <code>{row.actor_id}</code> → target <code>{row.target_id}</code>\n"
        f"{row.reason[:120]}"
        for row in rows
    ]
    await message.answer("📋 <b>Recent admin actions — this group</b>\n" + "\n\n".join(lines))


def _valid_group_admin_context(message: Message, bot: Bot) -> bool:
    return message.chat.type in GROUP_TYPES and message.from_user is not None


@router.message(Command("save"))
async def save_note(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can save notes.")
        return
    name = _args(message).split(maxsplit=1)[0].lower() if _args(message) else ""
    source = message.reply_to_message
    if not name or not re.fullmatch(r"[a-z0-9_-]{1,64}", name) or source is None or not (source.text or source.caption):
        await message.answer("Reply to a text message: /save NAME")
        return
    body = source.text or source.caption or ""
    async with database.sessions() as session:
        async with session.begin():
            group = await session.get(Group, message.chat.id)
            if group is None:
                session.add(Group(chat_id=message.chat.id, title=message.chat.title or ""))
                await session.flush()
            row = (await session.scalars(select(Note).where(Note.chat_id == message.chat.id, Note.name == name))).first()
            if row:
                row.content, row.creator_id = body[:4000], message.from_user.id
            else:
                session.add(Note(chat_id=message.chat.id, name=name, content=body[:4000], creator_id=message.from_user.id))
    await message.answer(f"✅ Saved group note <b>{name}</b>.")


@router.message(Command("get"))
async def get_note(message: Message, database: Database):
    name = _args(message).split(maxsplit=1)[0].lower() if _args(message) else ""
    if message.chat.type not in GROUP_TYPES or not name:
        await message.answer("Usage inside a group: /get NAME")
        return
    async with database.sessions() as session:
        row = (await session.scalars(select(Note).where(Note.chat_id == message.chat.id, Note.name == name))).first()
    if row is None:
        await message.answer("That note does not exist in this group.")
        return
    import html
    await message.answer(f"🗒️ <b>{html.escape(name)}</b>\n{html.escape(row.content)}")


@router.message(Command("notes"))
async def list_notes(message: Message, database: Database):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("Use /notes inside a group.")
        return
    async with database.sessions() as session:
        rows = (await session.scalars(select(Note).where(Note.chat_id == message.chat.id).order_by(Note.name).limit(50))).all()
    await message.answer("🗒️ Saved notes: " + (", ".join(row.name for row in rows) if rows else "none"))


@router.message(Command("filter"))
async def add_filter(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can manage filters.")
        return
    raw = _args(message)
    if "=>" not in raw:
        await message.answer("Usage: /filter keyword => automatic response")
        return
    trigger, response = (part.strip() for part in raw.split("=>", 1))
    if not trigger or len(trigger) > 100 or not response or len(response) > 1000:
        await message.answer("Trigger must be 1–100 characters and response 1–1000 characters.")
        return
    async with database.sessions() as session:
        async with session.begin():
            group = await session.get(Group, message.chat.id)
            if group is None:
                session.add(Group(chat_id=message.chat.id, title=message.chat.title or ""))
                await session.flush()
            row = (await session.scalars(select(GroupFilter).where(GroupFilter.chat_id == message.chat.id, GroupFilter.trigger == trigger.casefold()))).first()
            if row:
                row.response, row.creator_id = response, message.from_user.id
            else:
                session.add(GroupFilter(chat_id=message.chat.id, trigger=trigger.casefold(), response=response, creator_id=message.from_user.id))
    await message.answer(f"✅ Filter <b>{trigger}</b> saved for this group.")


@router.message(Command("stop"))
async def remove_filter(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can remove filters.")
        return
    trigger = _args(message).casefold()
    if not trigger:
        await message.answer("Usage: /stop KEYWORD")
        return
    async with database.sessions() as session:
        async with session.begin():
            row = (await session.scalars(select(GroupFilter).where(GroupFilter.chat_id == message.chat.id, GroupFilter.trigger == trigger))).first()
            if row:
                await session.delete(row)
    await message.answer("✅ Filter removed." if row else "No matching filter in this group.")


@router.message(Command("filters"))
async def list_filters(message: Message, database: Database):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("Use /filters inside a group.")
        return
    async with database.sessions() as session:
        rows = (await session.scalars(select(GroupFilter).where(GroupFilter.chat_id == message.chat.id).order_by(GroupFilter.trigger).limit(50))).all()
    await message.answer("🔎 Group filters: " + (", ".join(row.trigger for row in rows) if rows else "none"))


@router.message(F.text & ~F.text.startswith("/"))
async def match_group_filter(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.text or not message.from_user or message.from_user.is_bot:
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        rows = (await session.scalars(select(GroupFilter).where(GroupFilter.chat_id == message.chat.id).limit(100))).all()
        blocked = (await session.scalars(select(BlockedTerm).where(BlockedTerm.chat_id == message.chat.id).limit(200))).all()
        locks = await repo.get_setting(session, message.chat.id, "locks", [])
        antiflood = await repo.get_setting(session, message.chat.id, "antiflood_enabled", False)
    text_value = message.text.casefold()
    blocked_match = next((term for term in blocked if term.term in text_value), None)
    link_entities = any(entity.type in {"url", "text_link"} for entity in (message.entities or []))
    lock_match = (
        ("links" in locks and link_entities)
        or ("photos" in locks and bool(message.photo))
        or ("videos" in locks and bool(message.video or message.video_note or message.animation))
        or ("documents" in locks and bool(message.document or message.audio or message.voice))
        or ("stickers" in locks and bool(message.sticker))
        or ("media" in locks and bool(message.photo or message.video or message.document or message.audio or message.voice or message.sticker or message.animation))
    )
    flood_hit = False
    if antiflood:
        key = (message.chat.id, message.from_user.id)
        now = time.monotonic()
        window = _FLOOD_WINDOWS[key]
        while window and now - window[0] > 8:
            window.popleft()
        window.append(now)
        if len(window) > 5:
            flood_hit = True
            window.clear()
        if len(_FLOOD_WINDOWS) > 5000:
            _FLOOD_WINDOWS.clear()
    if blocked_match or lock_match or flood_hit:
        try:
            await bot.delete_message(message.chat.id, message.message_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
        return
    for row in rows:
        if row.trigger in text_value:
            import html
            await message.answer(html.escape(row.response))
            return


@router.message(Command("welcome"))
async def welcome_toggle(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can configure welcome messages.")
        return
    value = _args(message).lower()
    if value not in {"on", "off"}:
        await message.answer("Usage: /welcome on OR /welcome off")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            await repo.set_setting(session, message.chat.id, "welcome_enabled", value == "on")
    await message.answer(f"✅ Welcome messages turned {value} for this group.")


@router.message(Command("setwelcome"))
async def set_welcome_text(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can set the welcome text.")
        return
    template = _args(message)
    if not template or len(template) > 1000:
        await message.answer("Usage: /setwelcome Welcome {mention}! Keep it under 1000 characters. Supported: {first}, {name}, {id}, {mention}.")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            await repo.set_setting(session, message.chat.id, "welcome_template", template)
    await message.answer("✅ Welcome message template saved.")


@router.chat_member()
async def greet_new_member(event: ChatMemberUpdated, bot: Bot, database: Database):
    if event.chat.type not in GROUP_TYPES:
        return
    old_status, new_status = event.old_chat_member.status, event.new_chat_member.status
    active = {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
    if old_status in active or new_status not in active:
        return
    user = event.new_chat_member.user
    if user.is_bot:
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        antiraid_enabled = await repo.get_setting(session, event.chat.id, "antiraid_enabled", False)
    if antiraid_enabled:
        from app.services.antiraid import record_join_and_claim_alert
        async with database.sessions() as session:
            async with session.begin():
                should_alert = await record_join_and_claim_alert(session, chat_id=event.chat.id, user_id=user.id)
        if should_alert:
            try:
                admins = await bot.get_chat_administrators(event.chat.id)
                for admin in admins:
                    if not admin.user.is_bot:
                        try:
                            await bot.send_message(admin.user.id, "Anti-raid alert: 5 new members joined within 30 seconds. Review recent joins; no automatic bans or mass actions were taken.")
                        except (TelegramBadRequest, TelegramForbiddenError):
                            pass
            except (TelegramBadRequest, TelegramForbiddenError):
                pass
    async with database.sessions() as session:
        captcha_enabled = await repo.get_setting(session, event.chat.id, "captcha_enabled", False)
        enabled = await repo.get_setting(session, event.chat.id, "welcome_enabled", False)
        template = await repo.get_setting(session, event.chat.id, "welcome_template", "Welcome {mention}!")
    if captcha_enabled:
        try:
            member = await bot.get_chat_member(event.chat.id, user.id)
            if member.status not in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                chat = await bot.get_chat(event.chat.id)
                previous_permissions = member.permissions if member.status == ChatMemberStatus.RESTRICTED else chat.permissions
                if previous_permissions is not None:
                    a, b = random.randint(1, 9), random.randint(1, 9)
                    answer = a + b
                    choices = [answer, answer + 1, max(0, answer - 1)]
                    random.shuffle(choices)
                    saved_permissions = previous_permissions.model_dump(exclude_none=True)
                    async with database.sessions() as session:
                        async with session.begin():
                            challenge = CaptchaChallenge(chat_id=event.chat.id, user_id=user.id, answer=answer, choices_json=json.dumps(choices), previous_permissions_json=json.dumps(saved_permissions), expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
                            session.add(challenge)
                            await session.flush()
                            challenge_id = challenge.id
                    await bot.restrict_chat_member(event.chat.id, user.id, permissions=ChatPermissions(can_send_messages=False))
                    buttons = [[InlineKeyboardButton(text=str(value), callback_data=f"mxcap:{challenge_id}:{index}", style="success") for index, value in enumerate(choices)]]
                    await bot.send_message(event.chat.id, f"🧩 {user.full_name}, solve this to unlock chatting: {a} + {b} = ?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    if not enabled:
        return
    import html
    mention = f'<a href="tg://user?id={user.id}">{html.escape(user.full_name)}</a>'
    rendered = str(template).replace("{first}", html.escape(user.first_name)).replace("{name}", html.escape(user.full_name)).replace("{id}", str(user.id)).replace("{mention}", mention)
    await bot.send_message(event.chat.id, rendered[:4000])


@router.callback_query(F.data.startswith("mxcap:"))
async def verify_captcha(callback: CallbackQuery, bot: Bot, database: Database):
    try:
        _, raw_id, raw_index = (callback.data or "").split(":")
        challenge_id, selected_index = int(raw_id), int(raw_index)
    except (ValueError, AttributeError):
        await callback.answer("Invalid challenge.", show_alert=True)
        return
    async with database.sessions() as session:
        challenge = await session.get(CaptchaChallenge, challenge_id)
        if challenge is None or challenge.user_id != callback.from_user.id or challenge.status != "pending":
            await callback.answer("This challenge is invalid or already used.", show_alert=True)
            return
        chat_id, user_id = challenge.chat_id, challenge.user_id
        expires_at = challenge.expires_at
        previous_permissions_json = challenge.previous_permissions_json
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expired = expires_at < datetime.now(timezone.utc)
        choices = json.loads(challenge.choices_json)
        valid = not expired and 0 <= selected_index < len(choices) and choices[selected_index] == challenge.answer
        if not expired and not valid:
            await callback.answer("Incorrect answer. Try another option.", show_alert=True)
            return
        claim = await session.execute(
            update(CaptchaChallenge)
            .where(CaptchaChallenge.id == challenge_id, CaptchaChallenge.status == "pending")
            .values(status="processing")
        )
        await session.commit()
        if claim.rowcount != 1:
            await callback.answer("This challenge is already being processed.", show_alert=True)
            return
    try:
        chat = await bot.get_chat(chat_id)
        restore_permissions = ChatPermissions(**json.loads(previous_permissions_json)) if previous_permissions_json else chat.permissions
        if restore_permissions is None:
            async with database.sessions() as session:
                async with session.begin():
                    await session.execute(update(CaptchaChallenge).where(CaptchaChallenge.id == challenge_id, CaptchaChallenge.status == "processing").values(status="pending"))
            await callback.answer("Saved permissions unavailable; ask an admin.", show_alert=True)
            return
        await bot.restrict_chat_member(chat_id, user_id, permissions=restore_permissions)
    except (TelegramBadRequest, TelegramForbiddenError):
        async with database.sessions() as session:
            async with session.begin():
                await session.execute(update(CaptchaChallenge).where(CaptchaChallenge.id == challenge_id, CaptchaChallenge.status == "processing").values(status="pending"))
        await callback.answer("Could not restore group permissions. Please contact an admin.", show_alert=True)
        return
    async with database.sessions() as session:
        async with session.begin():
            final_status = "expired" if expired else "passed"
            await session.execute(update(CaptchaChallenge).where(CaptchaChallenge.id == challenge_id, CaptchaChallenge.status == "processing").values(status=final_status))
    if expired:
        await callback.message.edit_text("⌛ CAPTCHA expired. Your group permissions were restored; ask an admin if you still cannot chat.")
        await callback.answer("Expired.")
        return
    await callback.message.edit_text("✅ CAPTCHA passed. You can now chat.")
    await callback.answer("Verified!")


@router.message(Command("purge"))
async def purge_messages(message: Message, bot: Bot):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can purge messages.")
        return
    if message.reply_to_message is None:
        await message.answer("Reply to the first message to delete: /purge [count, 1–100].")
        return
    raw_count = _args(message).split(maxsplit=1)[0] if _args(message) else "1"
    if not raw_count.isdigit() or not 1 <= int(raw_count) <= 100:
        await message.answer("Count must be between 1 and 100.")
        return
    bot_member = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
    if bot_member.status != ChatMemberStatus.CREATOR and not getattr(bot_member, "can_delete_messages", False):
        await message.answer("I need the Telegram 'Delete messages' admin permission.")
        return
    start_id = message.reply_to_message.message_id
    end_id = start_id + int(raw_count) - 1
    deleted = 0
    for message_id in range(start_id, end_id + 1):
        try:
            await bot.delete_message(message.chat.id, message_id)
            deleted += 1
        except TelegramBadRequest:
            continue
        except TelegramForbiddenError:
            await message.answer("Telegram denied message deletion; stopping purge.")
            return
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    await message.answer(f"🧹 Purge complete: deleted {deleted} message(s).")


_LOCK_CATEGORIES = {"links", "photos", "videos", "documents", "stickers", "media"}


async def _set_lock(message: Message, bot: Bot, database: Database, *, enabled: bool):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can manage locks.")
        return
    category = _args(message).lower()
    if category not in _LOCK_CATEGORIES:
        await message.answer("Choose: links, photos, videos, documents, stickers, media.")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            current = await repo.get_setting(session, message.chat.id, "locks", [])
            values = set(current or [])
            values.add(category) if enabled else values.discard(category)
            await repo.set_setting(session, message.chat.id, "locks", sorted(values))
    await message.answer(f"🔒 {category} locked." if enabled else f"🔓 {category} unlocked.")


@router.message(Command("lock"))
async def lock_category(message: Message, bot: Bot, database: Database):
    await _set_lock(message, bot, database, enabled=True)


@router.message(Command("unlock"))
async def unlock_category(message: Message, bot: Bot, database: Database):
    await _set_lock(message, bot, database, enabled=False)


@router.message(Command("locks"))
async def show_locks(message: Message, database: Database):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("Use /locks inside a group.")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        values = await repo.get_setting(session, message.chat.id, "locks", [])
    await message.answer("🔐 Active locks: " + (", ".join(values) if values else "none"))


@router.message(Command("blocklist"))
async def manage_blocklist(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES:
        await message.answer("Use /blocklist inside a group.")
        return
    parts = _args(message).split(maxsplit=1)
    action = parts[0].lower() if parts else "list"
    if action == "list":
        async with database.sessions() as session:
            rows = (await session.scalars(select(BlockedTerm).where(BlockedTerm.chat_id == message.chat.id).order_by(BlockedTerm.term).limit(100))).all()
        await message.answer("🚫 Blocked terms: " + (", ".join(row.term for row in rows) if rows else "none"))
        return
    if not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can change the blocklist.")
        return
    if len(parts) < 2 or action not in {"add", "del", "remove"}:
        await message.answer("Usage: /blocklist add WORD or /blocklist del WORD; /blocklist lists terms.")
        return
    term = parts[1].strip().casefold()
    if not term or len(term) > 100:
        await message.answer("Term must be 1–100 characters.")
        return
    async with database.sessions() as session:
        async with session.begin():
            row = (await session.scalars(select(BlockedTerm).where(BlockedTerm.chat_id == message.chat.id, BlockedTerm.term == term))).first()
            if action == "add" and row is None:
                group = await session.get(Group, message.chat.id)
                if group is None:
                    session.add(Group(chat_id=message.chat.id, title=message.chat.title or ""))
                    await session.flush()
                session.add(BlockedTerm(chat_id=message.chat.id, term=term, creator_id=message.from_user.id))
            elif action in {"del", "remove"} and row is not None:
                await session.delete(row)
    await message.answer("✅ Blocklist updated.")


@router.message(Command("goodbye"))
async def goodbye_toggle(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can configure goodbye messages.")
        return
    value = _args(message).lower()
    if value not in {"on", "off"}:
        await message.answer("Usage: /goodbye on OR /goodbye off")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            await repo.set_setting(session, message.chat.id, "goodbye_enabled", value == "on")
    await message.answer(f"👋 Goodbye messages turned {value}.")


@router.chat_member()
async def goodbye_member(event: ChatMemberUpdated, bot: Bot, database: Database):
    if event.chat.type not in GROUP_TYPES:
        return
    leaving = {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
    if event.old_chat_member.status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED} or event.new_chat_member.status not in leaving:
        return
    user = event.old_chat_member.user
    if user.is_bot:
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        enabled = await repo.get_setting(session, event.chat.id, "goodbye_enabled", False)
    if enabled:
        import html
        await bot.send_message(event.chat.id, f"👋 {html.escape(user.full_name)} left the group.")


@router.message(F.photo | F.video | F.document | F.sticker | F.animation | F.voice | F.audio | F.video_note)
async def enforce_media_locks(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or message.from_user.is_bot:
        return
    if await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        locks = await repo.get_setting(session, message.chat.id, "locks", [])
    locked = (
        ("photos" in locks and bool(message.photo))
        or ("videos" in locks and bool(message.video or message.video_note or message.animation))
        or ("documents" in locks and bool(message.document or message.audio or message.voice))
        or ("stickers" in locks and bool(message.sticker))
        or ("media" in locks)
    )
    if locked:
        try:
            await bot.delete_message(message.chat.id, message.message_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            pass


@router.message(Command("antiflood"))
async def antiflood_toggle(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can configure antiflood.")
        return
    value = _args(message).lower()
    if value not in {"on", "off"}:
        await message.answer("Usage: /antiflood on OR /antiflood off. Deletes a user's 6th text message within 8 seconds.")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            await repo.set_setting(session, message.chat.id, "antiflood_enabled", value == "on")
    await message.answer(f"🌊 Antiflood turned {value}.")


@router.message(Command("closereport"))
async def close_report(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can close reports.")
        return
    raw_id = _args(message).split(maxsplit=1)[0] if _args(message) else ""
    if not raw_id.isdigit():
        await message.answer("Usage: /closereport REPORT_ID")
        return
    async with database.sessions() as session:
        async with session.begin():
            row = await session.get(ReportRecord, int(raw_id))
            if row is None or row.chat_id != message.chat.id:
                await message.answer("Report not found in this group.")
                return
            if row.status != "open":
                await message.answer("This report is already closed.")
                return
            row.status = "closed"
    await message.answer(f"✅ Report #{raw_id} closed for this group.")


@router.message(Command("resetwarnings"))
async def reset_warnings(message: Message, bot: Bot, database: Database):
    context = await _moderation_context(message, bot, require_bot_restrict=False)
    if not context:
        return
    actor, target = context
    async with database.sessions() as session:
        async with session.begin():
            from sqlalchemy import delete
            group = await session.get(Group, message.chat.id)
            if group is None:
                session.add(Group(chat_id=message.chat.id, title=message.chat.title or ""))
                await session.flush()
            result = await session.execute(delete(WarningRecord).where(
                WarningRecord.chat_id == message.chat.id,
                WarningRecord.user_id == target.id,
            ))
            removed = result.rowcount or 0
            session.add(ModerationAction(chat_id=message.chat.id, actor_id=actor.id, target_id=target.id, action="resetwarnings", reason=""))
    await message.answer(f"🧹 Removed {removed} warning(s) for {target.full_name} in this group.")



@router.message(Command("captcha"))
async def captcha_toggle(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can configure CAPTCHA.")
        return
    value = _args(message).lower()
    if value not in {"on", "off"}:
        await message.answer("Usage: /captcha on OR /captcha off. New non-admin members receive a 5-minute arithmetic challenge.")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            await repo.set_setting(session, message.chat.id, "captcha_enabled", value == "on")
    await message.answer(f"🧩 CAPTCHA turned {value}.")



@router.message(Command("antiraid"))
async def antiraid_toggle(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("Only group administrators can configure antiraid.")
        return
    value = _args(message).lower()
    if value not in {"on", "off"}:
        await message.answer("Usage: /antiraid on OR /antiraid off. Alerts admins after 5 joins in 30 seconds; no automatic bans.")
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            await repo.set_setting(session, message.chat.id, "antiraid_enabled", value == "on")
    await message.answer("Anti-raid alerts turned " + value + ".")


@router.message(Command("topic"))
async def manage_topic(message: Message, bot: Bot):
    if message.chat.type != ChatType.SUPERGROUP or not message.from_user:
        await message.answer("Forum topics are available in supergroups only.")
        return
    if not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("Only current group administrators can manage topics.")
        return
    try:
        actor = await bot.get_chat_member(message.chat.id, message.from_user.id)
        me = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
        if actor.status != ChatMemberStatus.CREATOR and not getattr(actor, "can_manage_topics", False):
            await message.answer("You need Telegram's Manage Topics permission.")
            return
        if me.status != ChatMemberStatus.CREATOR and not getattr(me, "can_manage_topics", False):
            await message.answer("I need Telegram's Manage Topics permission.")
            return
        chat = await bot.get_chat(message.chat.id)
        if not getattr(chat, "is_forum", False):
            await message.answer("This supergroup has forum topics disabled.")
            return
        parts = _args(message).split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        value = parts[1].strip() if len(parts) > 1 else ""
        if action == "create" and value:
            topic = await bot.create_forum_topic(message.chat.id, name=value[:128])
            await message.answer(f"Created topic <b>{topic.name}</b> (ID <code>{topic.message_thread_id}</code>).")
        elif action in {"close", "reopen", "delete"} and value.isdigit():
            topic_id = int(value)
            if action == "close":
                await bot.close_forum_topic(message.chat.id, topic_id)
            elif action == "reopen":
                await bot.reopen_forum_topic(message.chat.id, topic_id)
            else:
                await bot.delete_forum_topic(message.chat.id, topic_id)
            await message.answer(f"Topic {topic_id}: {action} completed.")
        else:
            await message.answer("Usage: /topic create NAME | /topic close ID | /topic reopen ID | /topic delete ID")
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.answer(f"Telegram rejected the topic operation: {str(exc)[:200]}")


@router.message(Command("export"))
async def export_group_config(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can export this group's settings.")
        return
    from app.services.group_config import export_config
    async with database.sessions() as session:
        rows = (await session.scalars(
            select(GroupSetting).where(GroupSetting.chat_id == message.chat.id).order_by(GroupSetting.key)
        )).all()
    payload = export_config(rows)
    if len(payload) > 3900:
        await message.answer("Configuration is too large to send as a message.")
        return
    await message.answer("<b>MASTER X group configuration export</b>\nCopy this JSON and reply to /import in the destination group:\n<pre>" + payload.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre>")


@router.message(Command("import"))
async def import_group_config(message: Message, bot: Bot, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can import settings into this group.")
        return
    source = message.reply_to_message
    raw = (source.text or source.caption or "") if source else ""
    if not raw:
        await message.answer("Reply to a MASTER X /export JSON message with /import.")
        return
    # Accept either a raw JSON document or the exported message's <pre> block.
    import re
    match = re.search(r"<pre>(.*?)</pre>", raw, flags=re.DOTALL)
    if match:
        raw = match.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    from app.services.group_config import validate_import
    try:
        settings = validate_import(raw)
    except ValueError as exc:
        await message.answer("⛔ Import rejected: " + str(exc))
        return
    repo = GroupRepository()
    async with database.sessions() as session:
        async with session.begin():
            await repo.ensure_group(session, message.chat.id, message.chat.title or "")
            for key, value in settings.items():
                await repo.set_setting(session, message.chat.id, key, value)
    await message.answer(f"✅ Imported {len(settings)} supported setting(s) into this group. Other groups were not changed.")


@router.message(Command("fed"))
async def federation_command(message: Message, bot: Bot, database: Database):
    """Manage this group's explicit federation membership; no cross-group action is automatic."""
    if message.chat.type not in GROUP_TYPES or not message.from_user:
        await message.answer("Use /fed inside a group.")
        return
    if not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can manage federation consent.")
        return
    parts = _args(message).split(maxsplit=1)
    action = parts[0].lower() if parts else "info"
    value = parts[1].strip() if len(parts) > 1 else ""
    from app.db.models import Federation, FederationGroup
    from app.services.federations import create_federation, delete_federation, federation_members, join_federation, leave_federation, rename_federation
    try:
        async with database.sessions() as session:
            async with session.begin():
                if action == "create" and value:
                    federation = await create_federation(session, name=value, chat_id=message.chat.id, actor_id=message.from_user.id)
                    response = f"✅ Federation <b>{federation.name}</b> created. This group opted in as its first member."
                elif action == "join" and value.isdigit():
                    await join_federation(session, federation_id=int(value), chat_id=message.chat.id, actor_id=message.from_user.id)
                    response = f"✅ This group explicitly joined federation #{value}."
                elif action == "leave":
                    membership = await session.scalar(select(FederationGroup).where(FederationGroup.chat_id == message.chat.id))
                    if membership is not None:
                        federation = await session.get(Federation, membership.federation_id)
                        if federation.owner_chat_id == message.chat.id:
                            response = "The owner group cannot leave while the federation exists. Use /fed delete to remove it."
                        else:
                            await leave_federation(session, chat_id=message.chat.id)
                            response = "This group left its federation."
                    else:
                        response = "This group is not in a federation."
                elif action == "rename" and value:
                    membership = await session.scalar(select(FederationGroup).where(FederationGroup.chat_id == message.chat.id))
                    if membership is None:
                        raise ValueError("This group has not opted into a federation.")
                    federation = await rename_federation(session, federation_id=membership.federation_id,
                                                          owner_chat_id=message.chat.id, name=value)
                    response = f"✅ Federation renamed to <b>{federation.name}</b>."
                elif action == "delete":
                    membership = await session.scalar(select(FederationGroup).where(FederationGroup.chat_id == message.chat.id))
                    if membership is None:
                        raise ValueError("This group has not opted into a federation.")
                    removed = await delete_federation(session, federation_id=membership.federation_id,
                                                      owner_chat_id=message.chat.id)
                    response = "✅ Federation deleted. All member opt-ins and federation ban records were removed."
                elif action == "info":
                    membership = await session.scalar(select(FederationGroup).where(FederationGroup.chat_id == message.chat.id))
                    if membership is None:
                        response = "This group has not opted into a federation."
                    else:
                        federation = await session.get(Federation, membership.federation_id)
                        members = await federation_members(session, membership.federation_id)
                        response = f"Federation <b>{federation.name}</b> (#{federation.id}) · {len(members)} opted-in group(s)."
                else:
                    response = "Usage: /fed create NAME | /fed join ID | /fed leave | /fed info | /fed rename NAME | /fed delete"
        await message.answer(response)
    except (ValueError, PermissionError) as exc:
        await message.answer("⛔ " + str(exc))


async def _federation_moderation(message: Message, bot: Bot, database: Database, *, revoke: bool) -> None:
    if message.chat.type not in GROUP_TYPES or message.from_user is None:
        await message.answer("Use this command inside a group.")
        return
    actor = message.from_user
    if actor.is_bot or not await has_group_admin_rights(bot, message.chat.id, actor.id):
        await message.answer("⛔ Only current group administrators can manage federation bans.")
        return
    try:
        actor_member = await bot.get_chat_member(message.chat.id, actor.id)
        me = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
        if actor_member.status != ChatMemberStatus.CREATOR and not getattr(actor_member, "can_restrict_members", False):
            await message.answer("⛔ You need Telegram's Ban Users permission.")
            return
        if me.status != ChatMemberStatus.CREATOR and (me.status != ChatMemberStatus.ADMINISTRATOR or not getattr(me, "can_restrict_members", False)):
            await message.answer("I need Telegram's Ban Users permission in this group.")
            return
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.answer(f"Telegram could not verify permissions: {str(exc)[:180]}")
        return

    target = message.reply_to_message.from_user if message.reply_to_message else None
    raw_parts = _args(message).split(maxsplit=1)
    if target is None and raw_parts and raw_parts[0].isdigit():
        target = User(id=int(raw_parts[0]), is_bot=False, first_name=f"User {raw_parts[0]}")
    if target is None:
        await message.answer("Reply to a member or provide a numeric Telegram USER_ID.")
        return
    if target.is_bot or target.id == actor.id:
        await message.answer("⛔ This target cannot be federation-moderated.")
        return
    reason = raw_parts[1] if len(raw_parts) > 1 else ""
    from app.db.models import FederationGroup
    from app.services.federations import (
        federation_for_group, federation_members, record_federation_ban,
        remove_federation_ban,
    )
    async with database.sessions() as session:
        async with session.begin():
            federation = await federation_for_group(session, message.chat.id)
            if federation is None:
                await message.answer("This group has not opted into a federation. Use /fed join ID first.")
                return
            federation_id = federation.id
            members = await federation_members(session, federation_id)
            if revoke:
                from app.services.federations import federation_ban_exists
                found = await federation_ban_exists(session, federation_id=federation_id, user_id=target.id)
            else:
                await record_federation_ban(session, federation_id=federation_id, user_id=target.id,
                                            actor_chat_id=message.chat.id, actor_id=actor.id, reason=reason)
                found = True
    if revoke and not found:
        await message.answer("No federation ban record exists for this user.")
        return

    applied, skipped, failed = [], [], []
    for chat_id in members:
        try:
            bot_member = await bot.get_chat_member(chat_id, (await bot.get_me()).id)
            if bot_member.status != ChatMemberStatus.CREATOR and (
                bot_member.status != ChatMemberStatus.ADMINISTRATOR
                or not getattr(bot_member, "can_restrict_members", False)
            ):
                skipped.append(f"{chat_id}: bot lacks Ban Users permission")
                continue
            try:
                target_member = await bot.get_chat_member(chat_id, target.id)
                if target_member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
                    skipped.append(f"{chat_id}: target is an administrator")
                    continue
            except TelegramBadRequest:
                # Not being a current member is normal for a ban by numeric ID.
                pass
            if revoke:
                await bot.unban_chat_member(chat_id, target.id, only_if_banned=True)
            else:
                await bot.ban_chat_member(chat_id, target.id)
            applied.append(str(chat_id))
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            failed.append(f"{chat_id}: {str(exc)[:100]}")
    if revoke and not failed and not skipped:
        async with database.sessions() as session:
            async with session.begin():
                await remove_federation_ban(session, federation_id=federation_id, user_id=target.id)
    action = "Unban" if revoke else "Ban"
    await message.answer(
        f"<b>Federation {action}</b> for user <code>{target.id}</code>\n"
        f"Successful: {len(applied)}/{len(members)}\n"
        + ("Applied in: " + ", ".join(applied[:15]) + "\n" if applied else "")
        + ("Skipped: " + "; ".join(skipped[:5]) + "\n" if skipped else "")
        + ("Failed: " + "; ".join(failed[:5]) if failed else "")
        + ("\nLedger updated; retry the command after fixing group permissions." if failed or skipped else "")
    )


@router.message(Command("fban"))
async def federation_ban_command(message: Message, bot: Bot, database: Database):
    await _federation_moderation(message, bot, database, revoke=False)


@router.message(Command("funban"))
async def federation_unban_command(message: Message, bot: Bot, database: Database):
    await _federation_moderation(message, bot, database, revoke=True)


@router.message(Command("privacy"))
async def privacy_command(message: Message, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.from_user:
        await message.answer("Use /privacy inside a group. /privacy shows scope; /privacy delete removes your records from this group.")
        return
    if message.from_user.is_bot:
        return
    action = _args(message).lower()
    if action != "delete":
        await message.answer(
            "🔐 <b>Group privacy</b>\n"
            "MASTER X stores group-scoped warnings, reports, moderation logs, notes, filters, blocked terms, and pending CAPTCHA challenges. "
            "Data is isolated by group. Use /privacy delete to erase records associated with your Telegram account in this group only. "
            "This does not delete Telegram messages or data in other groups."
        )
        return
    from app.services.privacy import erase_user_group_records
    async with database.sessions() as session:
        async with session.begin():
            counts = await erase_user_group_records(session, chat_id=message.chat.id, user_id=message.from_user.id)
    total = sum(counts.values())
    await message.answer(
        f"✅ Erased {total} group-scoped record(s) associated with your account: " +
        ", ".join(f"{key.replace('_', ' ')} {value}" for key, value in counts.items()) +
        ". Telegram messages and records in other groups are unaffected."
    )


@router.message(Command("format"))
async def format_command(message: Message):
    raw = _args(message)
    parts = raw.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Usage: /format bold|italic|code|quote TEXT")
        return
    from app.services.formatting import format_text
    try:
        rendered = format_text(parts[0], parts[1])
    except ValueError as exc:
        await message.answer("⛔ " + str(exc))
        return
    await message.answer(rendered)


@router.message(Command("clean"))
async def clean_messages(message: Message, bot: Bot):
    if message.chat.type not in GROUP_TYPES or not message.from_user or message.from_user.is_bot:
        await message.answer("Use /clean COUNT in a group.")
        return
    if not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only group administrators can clean messages.")
        return
    raw = _args(message)
    if not raw.isdigit() or not 1 <= int(raw) <= 20:
        await message.answer("Usage: /clean COUNT (1–20 messages, including this command).")
        return
    try:
        actor = await bot.get_chat_member(message.chat.id, message.from_user.id)
        me = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
        if actor.status != ChatMemberStatus.CREATOR and not getattr(actor, "can_delete_messages", False):
            await message.answer("⛔ You need Telegram's Delete Messages permission.")
            return
        if me.status != ChatMemberStatus.CREATOR and not getattr(me, "can_delete_messages", False):
            await message.answer("I need Telegram's Delete Messages permission.")
            return
        count = int(raw)
        ids = list(range(max(1, message.message_id - count + 1), message.message_id + 1))
        await bot.delete_messages(message.chat.id, ids)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        await message.answer(f"Telegram could not clean those messages: {str(exc)[:180]}")
