"""Preserve fractional marks from presentation scorecards."""

from alembic import op

revision = "0002_score_precision"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE competition.score_entry ALTER COLUMN points_delta decimal(10,2) NOT NULL")


def downgrade() -> None:
    raise RuntimeError("Downgrading score precision would lose fractional marks.")
