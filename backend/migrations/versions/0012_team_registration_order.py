"""Preserve source order for deterministic event-ranking ties."""

from alembic import op
import sqlalchemy as sa


revision = "0012_team_registration_order"
down_revision = "0011_round_max_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("team", sa.Column("registration_order", sa.SmallInteger(), nullable=True), schema="competition")


def downgrade() -> None:
    op.drop_column("team", "registration_order", schema="competition")
