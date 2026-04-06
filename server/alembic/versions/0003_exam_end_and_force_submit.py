"""add exam end fields and force submitted attempt status

Revision ID: 0003_exam_end_and_force_submit
Revises: 0002_answers_unique
Create Date: 2026-04-06 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_exam_end_and_force_submit"
down_revision: Union[str, None] = "0002_answers_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("is_ended", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("exams", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))

    op.drop_constraint("ck_attempts_status", "attempts", type_="check")
    op.create_check_constraint(
        "ck_attempts_status",
        "attempts",
        "status IN ('in_progress', 'submitted', 'force_submitted', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_attempts_status", "attempts", type_="check")
    op.create_check_constraint(
        "ck_attempts_status",
        "attempts",
        "status IN ('in_progress', 'submitted', 'cancelled')",
    )

    op.drop_column("exams", "ended_at")
    op.drop_column("exams", "is_ended")
