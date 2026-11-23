"""Operational snapshots and promotion eligibility."""

from alembic import op
import sqlalchemy as sa

revision = "uyaras_0002"
down_revision = "uyaras_0001"
branch_labels = None
depends_on = None


def upgrade():
    # Introspection allows a fresh 0001 metadata bootstrap as well as upgrades from existing V1 previews.
    additions = {
        "inventory": [
            sa.Column(
                "location", sa.String(80), nullable=False, server_default="primary"
            )
        ],
        "promotions": [
            sa.Column(
                "eligible_products", sa.JSON, nullable=False, server_default="[]"
            ),
            sa.Column(
                "eligible_categories", sa.JSON, nullable=False, server_default="[]"
            ),
        ],
        "order_items": [
            sa.Column("discount", sa.Integer, nullable=False, server_default="0"),
            sa.Column("included_tax", sa.Integer, nullable=False, server_default="0"),
        ],
        "return_requests": [
            sa.Column("condition", sa.String(300), nullable=False, server_default=""),
            sa.Column(
                "resolution_reference",
                sa.String(100),
                nullable=False,
                server_default="",
            ),
        ],
        "refunds": [
            sa.Column(
                "payment_attempt_id",
                sa.String(32),
                sa.ForeignKey("payment_attempts.id"),
                nullable=True,
            )
        ],
    }
    for table, columns in additions.items():
        existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)


def downgrade():
    for table, names in {
        "inventory": ["location"],
        "promotions": ["eligible_products", "eligible_categories"],
        "order_items": ["discount", "included_tax"],
        "return_requests": ["condition", "resolution_reference"],
        "refunds": ["payment_attempt_id"],
    }.items():
        for name in names:
            op.drop_column(table, name)
