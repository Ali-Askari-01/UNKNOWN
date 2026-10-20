"""Serialize shared rate-limit windows by bucket."""

import sqlalchemy as sa
from alembic import op


revision = "0004_rate_limit_buckets"
down_revision = "0003_shared_rate_limit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_bucket",
        sa.Column("bucket_key", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("bucket_key"),
        schema="competition",
    )


def downgrade() -> None:
    op.drop_table("rate_limit_bucket", schema="competition")
