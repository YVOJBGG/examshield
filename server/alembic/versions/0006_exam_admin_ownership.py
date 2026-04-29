"""add admin ownership to exams

Revision ID: 0006_exam_admin_ownership
Revises: 0005_exam_builder_foundation, 0003_exam_end_and_force_submit
Create Date: 2026-04-29 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_exam_admin_ownership"
down_revision: Union[str, tuple[str, str], None] = (
    "0005_exam_builder_foundation",
    "0003_exam_end_and_force_submit",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_exams_created_by_user_id"), "exams", ["created_by_user_id"], unique=False)
    op.create_foreign_key(
        "fk_exams_created_by_user_id_users",
        "exams",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_exams_created_by_user_id_users", "exams", type_="foreignkey")
    op.drop_index(op.f("ix_exams_created_by_user_id"), table_name="exams")
    op.drop_column("exams", "created_by_user_id")
