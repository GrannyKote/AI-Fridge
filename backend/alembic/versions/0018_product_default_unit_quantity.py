"""product.id_unit_of_measurement и quantity — умолчания для кладовой.

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-12
"""
from collections.abc import Sequence

from alembic import op

from app.schema_repair import apply_schema_repairs

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    apply_schema_repairs(op)


def downgrade() -> None:
    pass
