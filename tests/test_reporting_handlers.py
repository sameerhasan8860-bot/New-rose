import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.db.engine import Database
from app.db.models import ReportRecord
from app.handlers import report_message


def test_report_handler_persists_report_and_notifies_admins_best_effort():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        reporter = SimpleNamespace(id=101, is_bot=False)
        target = SimpleNamespace(id=202, is_bot=False)
        target_message = SimpleNamespace(from_user=target, message_id=303)
        message = SimpleNamespace(
            chat=SimpleNamespace(type="supergroup", id=-10001, title="Test group"),
            from_user=reporter,
            reply_to_message=target_message,
            text="/report spam",
            answer=AsyncMock(),
        )
        bot = SimpleNamespace(get_chat_administrators=AsyncMock(return_value=[]))
        await report_message(message, bot, db)

        async with db.sessions() as session:
            from sqlalchemy import select
            rows = (await session.scalars(select(ReportRecord).where(ReportRecord.chat_id == -10001))).all()
            assert len(rows) == 1
            assert rows[0].reporter_id == 101
            assert rows[0].target_id == 202
            assert rows[0].message_id == 303
            assert rows[0].reason == "spam"
            assert rows[0].status == "open"
        message.answer.assert_awaited_once()
        assert "Notified 0 admin(s)" in message.answer.await_args.args[0]
        bot.get_chat_administrators.assert_awaited_once_with(-10001)
        await db.close()
    asyncio.run(scenario())


def test_report_handler_rejects_missing_reply_without_database_write():
    async def scenario():
        db = Database("sqlite+aiosqlite:///:memory:")
        await db.create_schema()
        message = SimpleNamespace(
            chat=SimpleNamespace(type="supergroup", id=-10002, title="Test group"),
            from_user=SimpleNamespace(id=111),
            reply_to_message=None,
            text="/report",
            answer=AsyncMock(),
        )
        bot = SimpleNamespace(get_chat_administrators=AsyncMock())
        await report_message(message, bot, db)
        async with db.sessions() as session:
            from sqlalchemy import select
            assert (await session.scalars(select(ReportRecord))).all() == []
        message.answer.assert_awaited_once()
        bot.get_chat_administrators.assert_not_awaited()
        await db.close()
    asyncio.run(scenario())
