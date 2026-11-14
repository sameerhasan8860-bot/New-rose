"""Group-scoped self-service privacy operations."""
from sqlalchemy import delete, or_

from app.db.models import BlockedTerm, CaptchaChallenge, GroupFilter, ModerationAction, Note, ReportRecord, WarningRecord


async def erase_user_group_records(session, *, chat_id: int, user_id: int) -> dict[str, int]:
    """Delete records associated with a user in one group only; retain all other tenants."""
    warnings = await session.execute(delete(WarningRecord).where(
        WarningRecord.chat_id == chat_id,
        or_(WarningRecord.user_id == user_id, WarningRecord.actor_id == user_id),
    ))
    reports = await session.execute(delete(ReportRecord).where(
        ReportRecord.chat_id == chat_id,
        or_(ReportRecord.reporter_id == user_id, ReportRecord.target_id == user_id),
    ))
    actions = await session.execute(delete(ModerationAction).where(
        ModerationAction.chat_id == chat_id,
        or_(ModerationAction.actor_id == user_id, ModerationAction.target_id == user_id),
    ))
    return {
        "warnings": warnings.rowcount or 0,
        "reports": reports.rowcount or 0,
        "actions": actions.rowcount or 0,
    }
