"""Add persistent CAPTCHA challenges."""
from alembic import op
import sqlalchemy as sa

revision = "0005_phase3_captcha"
down_revision = "0004_phase3_blocked_terms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "captcha_challenges",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("answer", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_captcha_chat_user_status", "captcha_challenges", ["chat_id", "user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_captcha_chat_user_status", table_name="captcha_challenges")
    op.drop_table("captcha_challenges")
