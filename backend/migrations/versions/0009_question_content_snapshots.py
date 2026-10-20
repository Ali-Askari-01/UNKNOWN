"""Preserve complete question content in generated quiz sessions."""

from alembic import op
import sqlalchemy as sa


revision = "0009_question_content_snapshots"
down_revision = "0008_realtime_event_ordering"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quiz_question",
        sa.Column("code_snippet_snapshot", sa.Text(), nullable=True),
        schema="competition",
    )
    op.execute(
        sa.text(
            "UPDATE quiz_question "
            "SET code_snippet_snapshot = question.code_snippet "
            "FROM competition.quiz_question AS quiz_question "
            "JOIN competition.question AS question "
            "ON question.question_id = quiz_question.question_id "
            "WHERE quiz_question.code_snippet_snapshot IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("quiz_question", "code_snippet_snapshot", schema="competition")
