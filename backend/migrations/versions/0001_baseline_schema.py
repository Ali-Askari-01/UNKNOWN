"""Apply the reviewed SQL Server baseline schema.

Revision ID: 0001_baseline_schema
Revises:
"""
import re
from pathlib import Path

from alembic import op

revision = "0001_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[3] / "database" / "sqlserver" / "001_initial_schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    batches = re.split(r"^\s*GO\s*$", sql, flags=re.MULTILINE | re.IGNORECASE)
    for batch in batches:
        statement = batch.strip()
        if statement:
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError(
        "The baseline migration is intentionally non-destructive. Restore a database backup "
        "or create a reviewed rollback migration instead."
    )
