"""таблицы feedback и feedback_item

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0005"
down_revision: str | None = "0004"
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
    if _table_exists("feedback") is not True:
        op.create_table(
            "feedback",
            _id(),
            sa.Column("id_user", sa.Integer(), nullable=False),
            sa.Column("datetime_created", sa.DateTime(), nullable=False),
            sa.Column("feedback_text", sa.Text()),
            schema=SCHEMA,
        )

    if _table_exists("feedback_item") is not True:
        op.create_table(
            "feedback_item",
            _id(),
            sa.Column("id_feedback", sa.Integer(), nullable=False),
            sa.Column("item", sa.LargeBinary(), nullable=False),
            schema=SCHEMA,
        )


def downgrade() -> None:
    if _table_exists("feedback_item") is not False:
        op.drop_table("feedback_item", schema=SCHEMA)
    if _table_exists("feedback") is not False:
        op.drop_table("feedback", schema=SCHEMA)
