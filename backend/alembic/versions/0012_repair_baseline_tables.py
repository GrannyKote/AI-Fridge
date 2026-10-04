"""Таблицы baseline и авто-increment id на старых дампах.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-04

Регистрация пишет в created_user; вход — в login_attempt. На дампах, где была
только часть схемы, этих таблиц могло не быть. У id иногда нет sequence/default.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema

ID_TABLES: tuple[tuple[str, str], ...] = (
    ("user", f'"{SCHEMA}"."user"'),
    ("user_group", f'"{SCHEMA}".user_group'),
    ("user_group_user", f'"{SCHEMA}".user_group_user'),
    ("created_user", f'"{SCHEMA}".created_user'),
    ("login_attempt", f'"{SCHEMA}".login_attempt'),
)


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True)


def _table_exists(name: str) -> bool | None:
    if op.get_context().as_sql:
        return None
    return sa.inspect(op.get_bind()).has_table(name, schema=SCHEMA)


def _id_has_default(table: str) -> bool | None:
    if op.get_context().as_sql:
        return None
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table, schema=SCHEMA):
        return None
    id_col = next(
        (column for column in inspector.get_columns(table, schema=SCHEMA) if column["name"] == "id"),
        None,
    )
    if id_col is None:
        return None
    if id_col.get("identity"):
        return True
    default = id_col.get("default")
    return bool(default)


def _ensure_id_sequence(table: str, qualified: str) -> None:
    if _id_has_default(table):
        return

    seq = f"{table}_id_seq"
    op.execute(sa.text(f'CREATE SEQUENCE IF NOT EXISTS "{SCHEMA}".{seq}'))
    op.execute(
        sa.text(
            f"""
            SELECT setval(
                '"{SCHEMA}".{seq}',
                GREATEST(COALESCE((SELECT MAX(id) FROM {qualified}), 0) + 1, 1),
                false
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {qualified}
            ALTER COLUMN id SET DEFAULT nextval('"{SCHEMA}".{seq}')
            """
        )
    )
    op.execute(sa.text(f'ALTER SEQUENCE "{SCHEMA}".{seq} OWNED BY {qualified}.id'))


def upgrade() -> None:
    if _table_exists("created_user") is not True:
        op.create_table(
            "created_user",
            _id(),
            sa.Column("login", sa.String(512)),
            sa.Column("date_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("user_agent", sa.String(512), nullable=False),
            sa.Column("ip", sa.String(256), nullable=False),
            schema=SCHEMA,
        )

    if _table_exists("login_attempt") is not True:
        op.create_table(
            "login_attempt",
            _id(),
            sa.Column("login", sa.String(512), nullable=False),
            sa.Column("date_time", sa.Time(timezone=True), nullable=False),
            sa.Column("user_agent", sa.String(512), nullable=False),
            sa.Column("ip", sa.String(256), nullable=False),
            sa.Column("is_success", sa.Boolean(), nullable=False),
            schema=SCHEMA,
        )

    for table, qualified in ID_TABLES:
        _ensure_id_sequence(table, qualified)


def downgrade() -> None:
    pass
