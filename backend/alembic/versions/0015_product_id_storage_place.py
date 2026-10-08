"""product.id_storage_place — место хранения по умолчанию.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-08
"""
from collections.abc import Sequence

from alembic import op

from app.schema_repair import apply_schema_repairs

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    apply_schema_repairs(op)


def downgrade() -> None:
    pass
