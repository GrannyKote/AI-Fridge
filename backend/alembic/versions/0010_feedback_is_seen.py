"""feedback.is_seen и datetime_seen

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema

COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("is_seen", sa.Boolean()),
    ("datetime_seen", sa.DateTime(timezone=True)),
)


def _existing_columns() -> dict[str, sa.types.TypeEngine] | None:
    """None в режиме --sql: подключения нет, состояние базы неизвестно."""
    if op.get_context().as_sql:
        return None
    inspector = sa.inspect(op.get_bind())
    columns = inspector.get_columns("feedback", schema=SCHEMA)
    return {column["name"]: column["type"] for column in columns}


def upgrade() -> None:
    existing = _existing_columns()

    for name, type_ in COLUMNS:
        if existing is None or name not in existing:
            op.add_column("feedback", sa.Column(name, type_), schema=SCHEMA)

    op.execute(sa.text(f'UPDATE "{SCHEMA}".feedback SET is_seen = false WHERE is_seen IS NULL'))


def downgrade() -> None:
    existing = _existing_columns()
    for name, _ in reversed(COLUMNS):
        if existing is None or name in existing:
            op.drop_column("feedback", name, schema=SCHEMA)
