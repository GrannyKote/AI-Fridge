"""personal_news — ответы администратора на отзывы

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True)


def _table_exists(name: str) -> bool | None:
    if op.get_context().as_sql:
        return None
    return sa.inspect(op.get_bind()).has_table(name, schema=SCHEMA)


def _table_columns(name: str) -> set[str] | None:
    if op.get_context().as_sql:
        return None
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(name, schema=SCHEMA):
        return set()
    return {
        column["name"]
        for column in sa.inspect(bind).get_columns(name, schema=SCHEMA)
    }


def _create_personal_news_table() -> None:
    op.create_table(
        "personal_news",
        _id(),
        sa.Column("id_user", sa.Integer(), nullable=False),
        sa.Column("id_feedback", sa.Integer(), nullable=False),
        sa.Column("id_user_created", sa.Integer(), nullable=False),
        sa.Column("datetime_created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("header", sa.String(1024), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("datetime_seen", sa.DateTime(timezone=True)),
        schema=SCHEMA,
    )


def upgrade() -> None:
    columns = _table_columns("personal_news")
    if columns is None:
        return
    if columns and "id_feedback" not in columns:
        op.drop_table("personal_news", schema=SCHEMA)
        columns = set()
    if not columns:
        _create_personal_news_table()


def downgrade() -> None:
    if _table_exists("personal_news") is not False:
        op.drop_table("personal_news", schema=SCHEMA)
