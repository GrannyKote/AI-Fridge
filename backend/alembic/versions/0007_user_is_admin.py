"""user.is_admin — роль администратора

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema


def _existing_columns() -> dict[str, sa.types.TypeEngine] | None:
    """None в режиме --sql: подключения нет, состояние базы неизвестно."""
    if op.get_context().as_sql:
        return None
    inspector = sa.inspect(op.get_bind())
    columns = inspector.get_columns("user", schema=SCHEMA)
    return {column["name"]: column["type"] for column in columns}


def upgrade() -> None:
    existing = _existing_columns()

    # Колонка могла быть добавлена руками до появления этой ревизии.
    if existing is None or "is_admin" not in existing:
        op.add_column(
            "user",
            sa.Column("is_admin", sa.Boolean(), server_default=sa.false()),
            schema=SCHEMA,
        )

    op.execute(sa.text(f'UPDATE "{SCHEMA}"."user" SET is_admin = false WHERE is_admin IS NULL'))


def downgrade() -> None:
    existing = _existing_columns()
    if existing is None or "is_admin" in existing:
        op.drop_column("user", "is_admin", schema=SCHEMA)
