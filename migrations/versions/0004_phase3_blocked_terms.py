"""Add group-scoped blocked terms."""
from alembic import op
import sqlalchemy as sa

revision = "0004_phase3_blocked_terms"
down_revision = "0003_phase3_notes_filters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blocked_terms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False),
        sa.Column("term", sa.String(100), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_blocked_terms_chat_term", "blocked_terms", ["chat_id", "term"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_blocked_terms_chat_term", table_name="blocked_terms")
    op.drop_table("blocked_terms")
