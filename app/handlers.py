import re
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, ChatPermissions, Message, User
from sqlalchemy import func, select

from app.db.engine import Database
from app.db.models import Group, GroupFilter, GroupSetting, ModerationAction, Note, ReportRecord, WarningRecord
from app.db.repositories import GroupRepository
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
        "/unban accepts a replied user or numeric Telegram USER_ID. Admin rights and bot permissions are checked.\n\n/save NAME (reply) · /get NAME · /notes\n/filter keyword => response · /stop KEYWORD · /filters\n/welcome on|off · /setwelcome TEXT · /purge COUNT (reply, max 100)"
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
            defaults = chat.permissions or ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_change_info=True, can_invite_users=True, can_pin_messages=True, can_manage_topics=True)
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
async def match_group_filter(message: Message, database: Database):
    if message.chat.type not in GROUP_TYPES or not message.text or not message.from_user or message.from_user.is_bot:
        return
    async with database.sessions() as session:
        rows = (await session.scalars(select(GroupFilter).where(GroupFilter.chat_id == message.chat.id).limit(100))).all()
    text_value = message.text.casefold()
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
        enabled = await repo.get_setting(session, event.chat.id, "welcome_enabled", False)
        template = await repo.get_setting(session, event.chat.id, "welcome_template", "Welcome {mention}!")
    if not enabled:
        return
    import html
    mention = f'<a href="tg://user?id={user.id}">{html.escape(user.full_name)}</a>'
    rendered = str(template).replace("{first}", html.escape(user.first_name)).replace("{name}", html.escape(user.full_name)).replace("{id}", str(user.id)).replace("{mention}", mention)
    await bot.send_message(event.chat.id, rendered[:4000])


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
