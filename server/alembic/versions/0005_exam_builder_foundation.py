"""add exam builder foundation

Revision ID: 0005_exam_builder_foundation
Revises: 9c9f25b210e3
Create Date: 2026-03-26 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_exam_builder_foundation"
down_revision: Union[str, None] = "9c9f25b210e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column("exam_type", sa.String(length=20), nullable=False, server_default="written"),
    )
    op.add_column("exams", sa.Column("instructions", sa.Text(), nullable=True))
    op.create_check_constraint("ck_exams_exam_type", "exams", "exam_type IN ('mcq', 'written')")

    op.add_column("questions", sa.Column("points", sa.Float(), nullable=True, server_default="1"))
    op.add_column("questions", sa.Column("order_index", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            WITH ordered_questions AS (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY exam_id
                    ORDER BY created_at ASC, id ASC
                ) - 1 AS new_order_index
                FROM questions
            )
            UPDATE questions
            SET order_index = ordered_questions.new_order_index
            FROM ordered_questions
            WHERE questions.id = ordered_questions.id
            """
        )
    )
    op.alter_column("questions", "points", existing_type=sa.Float(), nullable=False, server_default=None)
    op.alter_column("questions", "order_index", existing_type=sa.Integer(), nullable=False, server_default=None)

    op.add_column("answers", sa.Column("selected_option_ids", sa.JSON(), nullable=True))
    op.alter_column("answers", "answer_text", existing_type=sa.Text(), nullable=True)

    op.create_table(
        "question_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_text", sa.String(length=500), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_options_question_id"), "question_options", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_question_options_question_id"), table_name="question_options")
    op.drop_table("question_options")

    op.execute(sa.text("UPDATE answers SET answer_text = '' WHERE answer_text IS NULL"))
    op.alter_column("answers", "answer_text", existing_type=sa.Text(), nullable=False)
    op.drop_column("answers", "selected_option_ids")

    op.drop_column("questions", "order_index")
    op.drop_column("questions", "points")

    op.drop_constraint("ck_exams_exam_type", "exams", type_="check")
    op.drop_column("exams", "instructions")
    op.drop_column("exams", "exam_type")
