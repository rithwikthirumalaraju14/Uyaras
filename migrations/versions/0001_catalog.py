from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = (Path(__file__).resolve().parents[2] / "app" / "schema_0001.sql").read_text()
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    for name in ("inventory_balance", "inventory_location", "variant", "product_category", "product", "category"):
        op.drop_table(name)
