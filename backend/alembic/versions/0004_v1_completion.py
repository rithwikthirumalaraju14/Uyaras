"""Catalog, cancellation, staff roles and channel-neutral notification metadata."""
from alembic import op
import sqlalchemy as sa

revision = "uyaras_0004"
down_revision = "uyaras_0003"
branch_labels = depends_on = None


def upgrade():
    op.alter_column("users", "role", type_=sa.String(40))
    for old, new in [("Catalog", "Catalog Manager"), ("Operations", "Operations Manager"),
                     ("Support", "Support Agent"), ("Analyst", "Read-only Analyst")]:
        op.execute(sa.text("UPDATE users SET role=:new WHERE role=:old").bindparams(old=old, new=new))
    for table, columns in {
        "products": [sa.Column("fabric", sa.Text(), nullable=False, server_default=""),
                     sa.Column("cod_allowed", sa.Boolean(), nullable=False, server_default=sa.true())],
        "variants": [sa.Column("regular_price", sa.Integer(), nullable=True)],
        "orders": [sa.Column("cancellation_reason", sa.String(300), nullable=False, server_default=""),
                   sa.Column("cancellation_previous", sa.String(30), nullable=False, server_default="")],
        "order_events": [sa.Column("actor", sa.String(80), nullable=False, server_default="system"),
                         sa.Column("source", sa.String(40), nullable=False, server_default="system"),
                         sa.Column("reference", sa.String(100), nullable=False, server_default=""),
                         sa.Column("detail", sa.JSON(), nullable=False, server_default="{}")],
        "outbox": [sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
                   sa.Column("template", sa.String(80), nullable=False, server_default="account"),
                   sa.Column("subject", sa.String(200), nullable=False, server_default="Uyaras account update")],
    }.items():
        for column in columns:
            op.add_column(table, column)
    op.create_check_constraint("variant_regular_price_valid", "variants", "regular_price IS NULL OR regular_price >= price")


def downgrade():
    op.drop_constraint("variant_regular_price_valid", "variants")
    for table, columns in {"outbox": ["channel", "template", "subject"],
                           "order_events": ["actor", "source", "reference", "detail"],
                           "orders": ["cancellation_reason", "cancellation_previous"],
                           "variants": ["regular_price"], "products": ["fabric", "cod_allowed"]}.items():
        for column in columns:
            op.drop_column(table, column)
    for old, new in [("Catalog", "Catalog Manager"), ("Operations", "Operations Manager"),
                     ("Support", "Support Agent"), ("Analyst", "Read-only Analyst"), ("Owner", "Administrator")]:
        op.execute(sa.text("UPDATE users SET role=:old WHERE role=:new").bindparams(old=old, new=new))
    op.alter_column("users", "role", type_=sa.String(20))
