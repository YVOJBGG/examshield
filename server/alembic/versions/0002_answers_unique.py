"""add unique constraint for answers attempt/question

Revision ID: 0002_answers_unique
Revises: 0001_initial_schema
Create Date: 2026-03-08 14:20:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_answers_unique"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_answers_attempt_question",
        "answers",
        ["attempt_id", "question_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_answers_attempt_question", "answers", type_="unique")
