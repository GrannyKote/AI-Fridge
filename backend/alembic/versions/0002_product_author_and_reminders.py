"""product: автор, время создания, дни напоминаний и срок хранения

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema

COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("id_user_created", sa.Integer()),
    ("datetime_created", sa.DateTime(timezone=True)),
    ("first_reminder_days", sa.SmallInteger()),
    ("second_reminder_days", sa.SmallInteger()),
    ("expires_in", sa.SmallInteger()),
)


def _existing_columns() -> dict[str, sa.types.TypeEngine] | None:
    """None в режиме --sql: подключения нет, состояние базы неизвестно."""
    if op.get_context().as_sql:
        return None
    inspector = sa.inspect(op.get_bind())
    columns = inspector.get_columns("product", schema=SCHEMA)
    return {column["name"]: column["type"] for column in columns}


def _normalize(existing: dict[str, sa.types.TypeEngine]) -> None:
    """Приводит колонки к целевому виду, если они заведены руками или черновиком ревизии."""
    if "id_user" in existing:
        # Автор продукта сначала назывался id_user.
        op.alter_column(
            "product", "id_user", new_column_name="id_user_created", schema=SCHEMA
        )
        existing["id_user_created"] = existing.pop("id_user")

    created = existing.get("datetime_created")
    if created is not None and not isinstance(created, sa.DateTime):
        # Время создания сначала хранилось как time, без даты.
        op.alter_column(
            "product",
            "datetime_created",
            type_=sa.DateTime(timezone=True),
            # Старые значения без даты восстановить нельзя, поэтому обнуляем.
            postgresql_using="NULL",
            schema=SCHEMA,
        )


def upgrade() -> None:
    existing = _existing_columns()

    if existing is not None:
        _normalize(existing)

    for name, type_ in COLUMNS:
        # Колонки могли быть добавлены руками до появления этой ревизии.
        if existing is None or name not in existing:
            op.add_column("product", sa.Column(name, type_), schema=SCHEMA)


def downgrade() -> None:
    existing = _existing_columns()

    for name, _ in reversed(COLUMNS):
        if existing is None or name in existing:
            op.drop_column("product", name, schema=SCHEMA)
