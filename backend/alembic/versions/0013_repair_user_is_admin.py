"""Повторно добавляет user.is_admin, если ревизия уже на head без колонки.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-04

На дампах alembic_version иногда оказывается на head (stamp), а DDL 0007/0011
не применялся — тогда SELECT по User падает с UndefinedColumn.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema


def _user_columns() -> dict[str, sa.types.TypeEngine] | None:
    if op.get_context().as_sql:
        return None
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("user", schema=SCHEMA):
        return {}
    return {
        column["name"]: column["type"]
        for column in inspector.get_columns("user", schema=SCHEMA)
    }


def upgrade() -> None:
    user_cols = _user_columns()
    if user_cols is not None and user_cols and "is_admin" not in user_cols:
        op.add_column(
            "user",
            sa.Column("is_admin", sa.Boolean(), server_default=sa.false()),
            schema=SCHEMA,
        )
    if user_cols is not None and user_cols:
        op.execute(
            sa.text(f'UPDATE "{SCHEMA}"."user" SET is_admin = false WHERE is_admin IS NULL')
        )


def downgrade() -> None:
    pass
