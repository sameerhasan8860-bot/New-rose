"""Add atomic update-processing leases."""
from alembic import op
import sqlalchemy as sa

revision = "0006_update_claims"
down_revision = "0005_phase3_captcha"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "update_claims",
        sa.Column("update_id", sa.BigInteger(), primary_key=True),
        sa.Column("owner_token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_update_claims_expiry", "update_claims", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_update_claims_expiry", table_name="update_claims")
    op.drop_table("update_claims")
