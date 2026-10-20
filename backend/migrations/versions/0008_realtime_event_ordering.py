"""Serialize realtime event identity allocation across API workers."""

import sqlalchemy as sa
from alembic import op

revision = "0008_realtime_event_ordering"
down_revision = "0007_quiz_session_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quiz_realtime_relay_lock",
        sa.Column("lock_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("lock_id"),
        schema="competition",
    )
    op.bulk_insert(
        sa.table(
            "quiz_realtime_relay_lock",
            sa.column("lock_id", sa.Integer()),
            sa.column("lock_version", sa.Integer()),
            schema="competition",
        ),
        [{"lock_id": 1, "lock_version": 0}],
    )


def downgrade() -> None:
    op.drop_table("quiz_realtime_relay_lock", schema="competition")
