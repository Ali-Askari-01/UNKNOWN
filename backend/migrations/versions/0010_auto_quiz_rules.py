"""Snapshot answer keys and question types for automatic quiz grading."""

import sqlalchemy as sa
from alembic import op

revision = "0010_auto_quiz_rules"
down_revision = "0009_question_content_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question", sa.Column("accepted_answers", sa.Text(), nullable=True), schema="competition")
    op.add_column("quiz_question", sa.Column("question_type_snapshot", sa.String(length=30), nullable=True), schema="competition")
    op.add_column("quiz_question", sa.Column("accepted_answers_snapshot", sa.Text(), nullable=True), schema="competition")
    op.execute(
        sa.text(
            "UPDATE quiz_question "
            "SET question_type_snapshot = question.question_type, "
            "accepted_answers_snapshot = question.accepted_answers "
            "FROM competition.quiz_question AS quiz_question "
            "JOIN competition.question AS question "
            "ON question.question_id = quiz_question.question_id "
            "WHERE quiz_question.question_type_snapshot IS NULL"
        )
    )
    op.alter_column(
        "quiz_question",
        "question_type_snapshot",
        existing_type=sa.String(length=30),
        nullable=False,
        schema="competition",
    )


def downgrade() -> None:
    op.drop_column("quiz_question", "accepted_answers_snapshot", schema="competition")
    op.drop_column("quiz_question", "question_type_snapshot", schema="competition")
    op.drop_column("question", "accepted_answers", schema="competition")
