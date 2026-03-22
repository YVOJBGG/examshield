"""add attempt grading fields

Revision ID: 0004_attempt_grading_fields
Revises: 0003_add_exam_code
Create Date: 2026-03-22 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_attempt_grading_fields"
down_revision: Union[str, None] = "0003_add_exam_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attempts", sa.Column("score", sa.Float(), nullable=True))
    op.add_column("attempts", sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("attempts", sa.Column("graded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_attempts_graded_by_user_id"), "attempts", ["graded_by_user_id"], unique=False)
    op.create_foreign_key(
        "fk_attempts_graded_by_user_id_users",
        "attempts",
        "users",
        ["graded_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_attempts_graded_by_user_id_users", "attempts", type_="foreignkey")
    op.drop_index(op.f("ix_attempts_graded_by_user_id"), table_name="attempts")
    op.drop_column("attempts", "graded_by_user_id")
    op.drop_column("attempts", "graded_at")
    op.drop_column("attempts", "score")
