"""Create initial Phase 2 tenant and moderation tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_phase2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("groups", sa.Column("chat_id", sa.BigInteger(), primary_key=True), sa.Column("title", sa.String(255), nullable=False, server_default=""), sa.Column("status", sa.String(24), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("group_settings", sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), primary_key=True), sa.Column("key", sa.String(100), primary_key=True), sa.Column("value_json", sa.Text(), nullable=False, server_default="null"), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("group_admins", sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), primary_key=True), sa.Column("user_id", sa.BigInteger(), primary_key=True), sa.Column("role", sa.String(24), nullable=False, server_default="admin"), sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("processed_updates", sa.Column("update_id", sa.BigInteger(), primary_key=True), sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("moderation_actions", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True), sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False), sa.Column("actor_id", sa.BigInteger(), nullable=False), sa.Column("target_id", sa.BigInteger(), nullable=False), sa.Column("action", sa.String(32), nullable=False), sa.Column("reason", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_moderation_chat_created", "moderation_actions", ["chat_id", "created_at"])
    op.create_table("warnings", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True), sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.BigInteger(), nullable=False), sa.Column("actor_id", sa.BigInteger(), nullable=False), sa.Column("reason", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_warnings_chat_user", "warnings", ["chat_id", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_warnings_chat_user", table_name="warnings")
    op.drop_table("warnings")
    op.drop_index("ix_moderation_chat_created", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_table("processed_updates")
    op.drop_table("group_admins")
    op.drop_table("group_settings")
    op.drop_table("groups")
