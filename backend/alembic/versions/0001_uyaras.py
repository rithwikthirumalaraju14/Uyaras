"""Frozen initial normalized schema. Later changes use new Alembic revisions."""

from pathlib import Path
from alembic import op

revision = "uyaras_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).with_name("0001_schema.sql").read_text(encoding="utf-8")
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for table in [
        "return_requests",
        "reservations",
        "refunds",
        "shipments",
        "payment_attempts",
        "order_items",
        "order_events",
        "inventory_movements",
        "inventory",
        "cod_ledger",
        "cart_items",
        "variants",
        "product_collections",
        "orders",
        "media",
        "sessions",
        "reset_tokens",
        "quotes",
        "products",
        "outbox",
        "addresses",
        "webhook_events",
        "users",
        "settings",
        "rate_limits",
        "promotions",
        "delivery_rules",
        "collections",
        "categories",
        "carts",
        "audit_log",
    ]:
        op.drop_table(table)
