"""Persist realtime events for cross-worker WebSocket delivery."""

import sqlalchemy as sa
from alembic import op

revision = "0006_quiz_realtime_events"
down_revision = "0005_idempotency_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quiz_realtime_event",
        sa.Column("realtime_event_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("should_broadcast", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["competition.quiz_session.quiz_session_id"]),
        sa.PrimaryKeyConstraint("realtime_event_id"),
        schema="competition",
    )
    op.create_index(
        "ix_quiz_realtime_event_session_id",
        "quiz_realtime_event",
        ["session_id"],
        schema="competition",
    )


def downgrade() -> None:
    op.drop_index("ix_quiz_realtime_event_session_id", table_name="quiz_realtime_event", schema="competition")
    op.drop_table("quiz_realtime_event", schema="competition")
