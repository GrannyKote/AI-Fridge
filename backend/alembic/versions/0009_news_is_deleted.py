"""news.is_deleted — мягкое удаление новостей

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema


def _existing_columns() -> dict[str, sa.types.TypeEngine] | None:
    """None в режиме --sql: подключения нет, состояние базы неизвестно."""
    if op.get_context().as_sql:
        return None
    inspector = sa.inspect(op.get_bind())
    columns = inspector.get_columns("news", schema=SCHEMA)
    return {column["name"]: column["type"] for column in columns}


def upgrade() -> None:
    existing = _existing_columns()

    if existing is None or "is_deleted" not in existing:
        op.add_column("news", sa.Column("is_deleted", sa.Boolean()), schema=SCHEMA)

    op.execute(sa.text(f'UPDATE "{SCHEMA}".news SET is_deleted = false WHERE is_deleted IS NULL'))


def downgrade() -> None:
    existing = _existing_columns()
    if existing is None or "is_deleted" in existing:
        op.drop_column("news", "is_deleted", schema=SCHEMA)
