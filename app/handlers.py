from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="core")

BRAND = "✦ 𝗠𝗔𝗦𝗧𝗘𝗥 𝗫 ✦"

@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        f"{BRAND}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Your community command center is coming online.\n\n"
        "🛡️ Moderation  •  ✨ Automation\n"
        "🤖 AI companion • 📊 Community insights\n\n"
        "Use /help to explore the commands available in this build.\n"
        "━━━━━━━━━━━━━━━━━━"
    )

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        f"{BRAND}\n"
        "𝗖𝗢𝗥𝗘 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦\n"
        " /start — Welcome\n"
        " /help — Available commands\n"
        " /settings — Settings status\n"
        " /about — About MASTER X\n"
        " /id — Chat and user IDs\n"
        " /ping — Runtime response\n"
        " /status — Basic health\n\n"
        "Advanced modules are planned and will appear here only after implementation."
    )

@router.message(Command("settings"))
async def settings(message: Message) -> None:
    await message.answer(
        "⚙️ 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦\n"
        "The group dashboard is under development. No settings have been changed."
    )

@router.message(Command("about"))
async def about(message: Message) -> None:
    await message.answer(
        f"{BRAND}\n"
        "A modular community-management platform.\n"
        "Independent project; not affiliated with Rose, Group Help, Iris, or Combot."
    )

@router.message(Command("id"))
async def ids(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else "unknown"
    await message.answer(f"🆔 Chat ID: <code>{message.chat.id}</code>\nUser ID: <code>{user_id}</code>", parse_mode="HTML")

@router.message(Command("ping"))
async def ping(message: Message) -> None:
    await message.answer("🏓 Pong — MASTER X is responding.")

@router.message(Command("status"))
async def status(message: Message) -> None:
    await message.answer("🟢 Process is online. Advanced modules are not enabled in this build.")
