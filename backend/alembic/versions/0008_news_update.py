"""таблица news_update — журнал правок новостей

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True)


def _table_exists(name: str) -> bool | None:
    """None в режиме --sql: подключения нет, состояние базы неизвестно."""
    if op.get_context().as_sql:
        return None
    return sa.inspect(op.get_bind()).has_table(name, schema=SCHEMA)


def upgrade() -> None:
    if _table_exists("news_update") is not True:
        op.create_table(
            "news_update",
            _id(),
            sa.Column("id_user_updated", sa.Integer(), nullable=False),
            sa.Column("datetime_updated", sa.DateTime(timezone=True), nullable=False),
            schema=SCHEMA,
        )


def downgrade() -> None:
    if _table_exists("news_update") is not False:
        op.drop_table("news_update", schema=SCHEMA)
