"""Store retry-safe mutation responses."""

import sqlalchemy as sa
from alembic import op

revision = "0005_idempotency_records"
down_revision = "0004_rate_limit_buckets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_record",
        sa.Column("idempotency_record_id", sa.Uuid(), nullable=False),
        sa.Column("scope_key", sa.String(length=240), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_record_id"),
        sa.UniqueConstraint("scope_key", "idempotency_key", name="uq_idempotency_scope_key"),
        schema="competition",
    )


def downgrade() -> None:
    op.drop_table("idempotency_record", schema="competition")
