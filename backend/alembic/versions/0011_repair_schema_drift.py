"""Повторно накатывает пропущенные изменения, если alembic_version уже на head.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-03

На старых базах ревизии 0002–0010 могли быть отмечены без реального DDL
(например после stamp head). Все операции идемпотентны.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = settings.db_schema

PRODUCT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("id_user_created", sa.Integer()),
    ("datetime_created", sa.DateTime(timezone=True)),
    ("first_reminder_days", sa.SmallInteger()),
    ("second_reminder_days", sa.SmallInteger()),
    ("expires_in", sa.SmallInteger()),
)

UGP_FIRST_REMINDER: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("first_reminder_shown", sa.DateTime(timezone=True)),
    ("first_reminder_seen", sa.DateTime(timezone=True)),
)

UGP_SECOND_REMINDER: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("second_reminder_shown", sa.DateTime(timezone=True)),
    ("second_reminder_seen", sa.DateTime(timezone=True)),
)

# В baseline 0001 есть price; в старых дампах колонки могло не быть.
UGP_BASELINE_EXTRA: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("price", sa.Numeric()),
)


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True)


def _table_columns(table: str) -> dict[str, sa.types.TypeEngine] | None:
    if op.get_context().as_sql:
        return None
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table, schema=SCHEMA):
        return {}
    columns = inspector.get_columns(table, schema=SCHEMA)
    return {column["name"]: column["type"] for column in columns}


def _table_exists(name: str) -> bool | None:
    if op.get_context().as_sql:
        return None
    return sa.inspect(op.get_bind()).has_table(name, schema=SCHEMA)


def _add_columns(
    table: str,
    columns: tuple[tuple[str, sa.types.TypeEngine], ...],
    existing: dict[str, sa.types.TypeEngine] | None,
) -> None:
    if existing is None:
        return
    for name, type_ in columns:
        if name not in existing:
            op.add_column(table, sa.Column(name, type_), schema=SCHEMA)


def _normalize_product(existing: dict[str, sa.types.TypeEngine]) -> None:
    if "id_user" in existing:
        op.alter_column(
            "product", "id_user", new_column_name="id_user_created", schema=SCHEMA
        )
        existing["id_user_created"] = existing.pop("id_user")

    created = existing.get("datetime_created")
    if created is not None and not isinstance(created, sa.DateTime):
        op.alter_column(
            "product",
            "datetime_created",
            type_=sa.DateTime(timezone=True),
            postgresql_using="NULL",
            schema=SCHEMA,
        )


def upgrade() -> None:
    product_cols = _table_columns("product")
    if product_cols is not None and product_cols:
        _normalize_product(product_cols)
        _add_columns("product", PRODUCT_COLUMNS, product_cols)

    ugp_cols = _table_columns("user_group_product")
    if ugp_cols is not None and ugp_cols:
        _add_columns("user_group_product", UGP_BASELINE_EXTRA, ugp_cols)
        _add_columns("user_group_product", UGP_FIRST_REMINDER, ugp_cols)
        _add_columns("user_group_product", UGP_SECOND_REMINDER, ugp_cols)

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

    user_cols = _table_columns("user")
    if user_cols is not None and user_cols and "is_admin" not in user_cols:
        op.add_column(
            "user",
            sa.Column("is_admin", sa.Boolean(), server_default=sa.false()),
            schema=SCHEMA,
        )
    if user_cols is not None and user_cols:
        op.execute(
            sa.text(f'UPDATE "{SCHEMA}"."user" SET is_admin = false WHERE is_admin IS NULL')
        )

    if _table_exists("news_update") is not True:
        op.create_table(
            "news_update",
            _id(),
            sa.Column("id_user_updated", sa.Integer(), nullable=False),
            sa.Column("datetime_updated", sa.DateTime(timezone=True), nullable=False),
            schema=SCHEMA,
        )

    news_cols = _table_columns("news")
    if news_cols is not None and news_cols and "is_deleted" not in news_cols:
        op.add_column("news", sa.Column("is_deleted", sa.Boolean()), schema=SCHEMA)
    if news_cols is not None and news_cols:
        op.execute(
            sa.text(f'UPDATE "{SCHEMA}".news SET is_deleted = false WHERE is_deleted IS NULL')
        )

    feedback_cols = _table_columns("feedback")
    if feedback_cols is not None and feedback_cols:
        if "is_seen" not in feedback_cols:
            op.add_column("feedback", sa.Column("is_seen", sa.Boolean()), schema=SCHEMA)
        if "datetime_seen" not in feedback_cols:
            op.add_column(
                "feedback",
                sa.Column("datetime_seen", sa.DateTime(timezone=True)),
                schema=SCHEMA,
            )
        op.execute(
            sa.text(f'UPDATE "{SCHEMA}".feedback SET is_seen = false WHERE is_seen IS NULL')
        )


def downgrade() -> None:
    # Откат repair-ревизии не трогает схему — пропущенный DDL нельзя безопасно «отменить».
    pass
