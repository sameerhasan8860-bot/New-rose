"""Add explicitly consented federations and scoped federation bans."""
from alembic import op
import sqlalchemy as sa

revision = "0007_federations"
down_revision = "0006_update_claims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "federations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("owner_chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "federation_groups",
        sa.Column("federation_id", sa.Integer(), sa.ForeignKey("federations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("groups.chat_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("consented_by", sa.BigInteger(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_federation_groups_chat", "federation_groups", ["chat_id"], unique=True)
    op.create_table(
        "federation_bans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("federation_id", sa.Integer(), sa.ForeignKey("federations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_federation_bans_fed_user", "federation_bans", ["federation_id", "user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_federation_bans_fed_user", table_name="federation_bans")
    op.drop_table("federation_bans")
    op.drop_index("ix_federation_groups_chat", table_name="federation_groups")
    op.drop_table("federation_groups")
    op.drop_table("federations")
