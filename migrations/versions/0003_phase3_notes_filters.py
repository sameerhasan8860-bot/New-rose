"""Add group notes and keyword filters."""
from alembic import op
import sqlalchemy as sa

revision = "0003_phase3_notes_filters"
down_revision = "0002_phase3_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notes_chat_name", "notes", ["chat_id", "name"], unique=True)
    op.create_table(
        "group_filters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger", sa.String(100), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_filters_chat_trigger", "group_filters", ["chat_id", "trigger"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_filters_chat_trigger", table_name="group_filters")
    op.drop_table("group_filters")
    op.drop_index("ix_notes_chat_name", table_name="notes")
    op.drop_table("notes")
