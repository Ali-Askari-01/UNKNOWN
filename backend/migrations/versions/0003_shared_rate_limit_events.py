"""Store rate-limit events in the shared database."""

import sqlalchemy as sa
from alembic import op

revision = "0003_shared_rate_limit_events"
down_revision = "0002_score_precision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_event",
        sa.Column("rate_limit_event_id", sa.Uuid(), nullable=False),
        sa.Column("bucket_key", sa.String(length=240), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("rate_limit_event_id"),
        schema="competition",
    )
    op.create_index(
        "ix_rate_limit_event_bucket_time",
        "rate_limit_event",
        ["bucket_key", "occurred_at"],
        unique=False,
        schema="competition",
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_event_bucket_time", table_name="rate_limit_event", schema="competition")
    op.drop_table("rate_limit_event", schema="competition")
