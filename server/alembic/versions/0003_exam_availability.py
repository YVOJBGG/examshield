"""add exam availability

Revision ID: 0003_exam_availability
Revises: 0002_answers_unique
Create Date: 2026-03-23 12:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_exam_availability"
down_revision: Union[str, None] = "0002_answers_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("exams", "is_available")
