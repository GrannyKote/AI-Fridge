"""таблицы news и user_news_seen

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0006"
down_revision: str | None = "0005"
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
    if _table_exists("news") is not True:
        op.create_table(
            "news",
            _id(),
            sa.Column("id_user_created", sa.Integer(), nullable=False),
            sa.Column("datetime_created", sa.DateTime(timezone=True), nullable=False),
            sa.Column("header", sa.String(1024), nullable=False),
            sa.Column("body", sa.Text()),
            schema=SCHEMA,
        )

    if _table_exists("user_news_seen") is not True:
        op.create_table(
            "user_news_seen",
            _id(),
            sa.Column("id_news", sa.Integer(), nullable=False),
            sa.Column("id_user_seen", sa.Integer(), nullable=False),
            sa.Column("datetime_seen", sa.DateTime(timezone=True), nullable=False),
            schema=SCHEMA,
        )


def downgrade() -> None:
    if _table_exists("user_news_seen") is not False:
        op.drop_table("user_news_seen", schema=SCHEMA)
    if _table_exists("news") is not False:
        op.drop_table("news", schema=SCHEMA)
