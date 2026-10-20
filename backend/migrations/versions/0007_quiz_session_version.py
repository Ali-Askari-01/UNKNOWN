"""Add optimistic concurrency control to quiz session actions."""

import sqlalchemy as sa
from alembic import op

revision = "0007_quiz_session_version"
down_revision = "0006_quiz_realtime_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quiz_session",
        sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"),
        schema="competition",
    )


def downgrade() -> None:
    op.drop_column("quiz_session", "version_id", schema="competition")
