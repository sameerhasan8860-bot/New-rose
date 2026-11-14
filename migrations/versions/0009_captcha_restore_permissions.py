"""Store member permissions before applying CAPTCHA restrictions."""
from alembic import op
import sqlalchemy as sa

revision = "0009_captcha_restore_permissions"
down_revision = "0008_persistent_antiraid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("captcha_challenges", sa.Column("previous_permissions_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("captcha_challenges", "previous_permissions_json")
