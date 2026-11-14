"""Persist antiraid join windows and deduplicate threshold alerts across workers."""
from alembic import op
import sqlalchemy as sa

revision = "0008_persistent_antiraid"
down_revision = "0007_federations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raid_join_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raid_join_chat_time", "raid_join_events", ["chat_id", "joined_at"])
    op.create_table(
        "raid_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False),
        sa.Column("threshold_event_id", sa.Integer(), sa.ForeignKey("raid_join_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raid_alert_chat_threshold", "raid_alerts", ["chat_id", "threshold_event_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_raid_alert_chat_threshold", table_name="raid_alerts")
    op.drop_table("raid_alerts")
    op.drop_index("ix_raid_join_chat_time", table_name="raid_join_events")
    op.drop_table("raid_join_events")
