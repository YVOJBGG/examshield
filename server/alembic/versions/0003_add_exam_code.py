"""add public exam code

Revision ID: 0003_add_exam_code
Revises: 0002_answers_unique
Create Date: 2026-03-22 17:00:00.000000
"""

from secrets import randbelow
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_add_exam_code"
down_revision: Union[str, None] = "0002_answers_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_unique_code(existing: set[str]) -> str:
    while True:
        code = f"{randbelow(1_000_000):06d}"
        if code not in existing:
            existing.add(code)
            return code


def upgrade() -> None:
    op.add_column("exams", sa.Column("exam_code", sa.String(length=6), nullable=True))

    connection = op.get_bind()
    exams = list(connection.execute(sa.text("SELECT id FROM exams")).fetchall())
    existing_codes: set[str] = set()

    for row in exams:
        code = _generate_unique_code(existing_codes)
        connection.execute(
            sa.text("UPDATE exams SET exam_code = :exam_code WHERE id = :exam_id"),
            {"exam_code": code, "exam_id": row.id},
        )

    op.alter_column("exams", "exam_code", existing_type=sa.String(length=6), nullable=False)
    op.create_unique_constraint("uq_exams_exam_code", "exams", ["exam_code"])
    op.create_index(op.f("ix_exams_exam_code"), "exams", ["exam_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_exams_exam_code"), table_name="exams")
    op.drop_constraint("uq_exams_exam_code", "exams", type_="unique")
    op.drop_column("exams", "exam_code")
