"""merge heads

Revision ID: 9c9f25b210e3
Revises: 0003_exam_availability, 0004_attempt_grading_fields
Create Date: 2026-03-23 17:49:45.947126
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c9f25b210e3'
down_revision = ('0003_exam_availability', '0004_attempt_grading_fields')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
