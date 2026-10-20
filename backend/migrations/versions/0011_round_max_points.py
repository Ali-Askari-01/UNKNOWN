"""Store official maximum points for normalized event rankings."""

import sqlalchemy as sa
from alembic import op

revision = "0011_round_max_points"
down_revision = "0010_auto_quiz_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("round", sa.Column("max_points", sa.Numeric(10, 2), nullable=True), schema="competition")


def downgrade() -> None:
    op.drop_column("round", "max_points", schema="competition")
