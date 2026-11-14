"""Group-scoped self-service privacy operations."""
from sqlalchemy import delete, or_

from app.db.models import BlockedTerm, CaptchaChallenge, GroupFilter, ModerationAction, Note, ReportRecord, WarningRecord


async def erase_user_group_records(session, *, chat_id: int, user_id: int) -> dict[str, int]:
    """Delete records associated with a user in one group only; retain all other tenants."""
    statements = {
        "warnings": delete(WarningRecord).where(WarningRecord.chat_id == chat_id, or_(WarningRecord.user_id == user_id, WarningRecord.actor_id == user_id)),
        "reports": delete(ReportRecord).where(ReportRecord.chat_id == chat_id, or_(ReportRecord.reporter_id == user_id, ReportRecord.target_id == user_id)),
        "actions": delete(ModerationAction).where(ModerationAction.chat_id == chat_id, or_(ModerationAction.actor_id == user_id, ModerationAction.target_id == user_id)),
        "notes": delete(Note).where(Note.chat_id == chat_id, Note.creator_id == user_id),
        "filters": delete(GroupFilter).where(GroupFilter.chat_id == chat_id, GroupFilter.creator_id == user_id),
        "blocked_terms": delete(BlockedTerm).where(BlockedTerm.chat_id == chat_id, BlockedTerm.creator_id == user_id),
        "captcha_challenges": delete(CaptchaChallenge).where(CaptchaChallenge.chat_id == chat_id, CaptchaChallenge.user_id == user_id),
    }
    counts = {}
    for key, statement in statements.items():
        result = await session.execute(statement)
        counts[key] = result.rowcount or 0
    return counts
