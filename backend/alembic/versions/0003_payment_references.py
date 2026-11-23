"""Provider references must be unique once supplied."""

from alembic import op

revision = "uyaras_0003"
down_revision = "uyaras_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE UNIQUE INDEX payment_reference_unique ON payment_attempts (provider, reference) WHERE reference <> ''"
    )


def downgrade():
    op.drop_index("payment_reference_unique", table_name="payment_attempts")
