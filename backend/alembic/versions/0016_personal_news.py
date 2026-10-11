"""таблица personal_news — новости для выбранных пользователей

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True)


def _table_exists(name: str) -> bool | None:
    if op.get_context().as_sql:
        return None
    return sa.inspect(op.get_bind()).has_table(name, schema=SCHEMA)


def upgrade() -> None:
    if _table_exists("personal_news") is not True:
        op.create_table(
            "personal_news",
            _id(),
            sa.Column("id_news", sa.Integer(), nullable=False),
            sa.Column("id_user", sa.Integer(), nullable=False),
            schema=SCHEMA,
        )


def downgrade() -> None:
    if _table_exists("personal_news") is not False:
        op.drop_table("personal_news", schema=SCHEMA)
