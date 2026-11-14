from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatType
from app.services.authorization import has_group_admin_rights

router = Router(name="core")

BRAND = "✦ 𝗠𝗔𝗦𝗧𝗘𝗥 𝗫 ✦"

@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        f"{BRAND}\\n"
        "━━━━━━━━━━━━━━━━━━\\n"
        "Your community command center is coming online.\\n\\n"
        "🛡️ Moderation  •  ✨ Automation\\n"
        "🤖 AI companion • 📊 Community insights\\n\\n"
        "Use /help to explore the commands available in this build.\\n"
        "━━━━━━━━━━━━━━━━━━"
    )

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        f"{BRAND}\\n"
        "𝗖𝗢𝗥𝗘 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦\\n"
        " /start — Welcome\\n"
        " /help — Available commands\\n"
        " /settings — Settings status (group admins)\\n"
        " /about — About MASTER X\\n"
        " /id — Chat and user IDs\\n"
        " /ping — Runtime response\\n"
        " /status — Basic health\\n\\n"
        "Advanced modules are planned and will appear here only after implementation."
    )

@router.message(Command("settings"))
async def settings_command(message: Message, bot: Bot) -> None:
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("⚙️ Group settings are available inside a group, for its administrators.")
        return
    if not message.from_user or not await has_group_admin_rights(bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Only current group administrators can access group settings.")
        return
    await message.answer(
        "⚙️ 𝗚𝗥𝗢𝗨𝗣 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦\\n"
        "Your group is isolated from every other group.\\n"
        "The interactive settings dashboard is still under development; no settings have been changed."
    )

@router.message(Command("about"))
async def about(message: Message) -> None:
    await message.answer(
        f"{BRAND}\\n"
        "A modular community-management platform.\\n"
        "Independent project; not affiliated with Rose, Group Help, Iris, or Combot."
    )

@router.message(Command("id"))
async def ids(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else "unknown"
    await message.answer(f"🆔 Chat ID: <code>{message.chat.id}</code>\\nUser ID: <code>{user_id}</code>")

@router.message(Command("ping"))
async def ping(message: Message) -> None:
    await message.answer("🏓 Pong — MASTER X is responding.")

@router.message(Command("status"))
async def status(message: Message) -> None:
    await message.answer("🟢 Process is online. Advanced modules are not enabled in this build.")
