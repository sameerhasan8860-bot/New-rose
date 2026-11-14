from aiogram import Bot
from aiogram.enums import ChatMemberStatus


async def is_global_owner(user_id: int, owner_ids: set[int]) -> bool:
    return user_id in owner_ids


async def has_group_admin_rights(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check Telegram live membership; cached DB roles are not authorization."""
    member = await bot.get_chat_member(chat_id, user_id)
    if member.status == ChatMemberStatus.CREATOR:
        return True
    if member.status != ChatMemberStatus.ADMINISTRATOR:
        return False
    return True
