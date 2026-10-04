"""Полное идемпотентное выравнивание схемы после restore бэкапа.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-04

После pg_restore alembic_version может совпадать с head, а DDL — из старого
дампа. Повторный upgrade head без новой ревизии ничего не делает; эта ревизия
и scripts/repair_schema.py вызывают alembic.schema_repair.apply_schema_repairs.
"""
from collections.abc import Sequence

from alembic import op

from app.schema_repair import apply_schema_repairs

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    apply_schema_repairs(op)


def downgrade() -> None:
    pass
