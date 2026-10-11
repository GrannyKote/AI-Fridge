"""Идемпотентное выравнивание схемы diplom_all с моделями приложения.

Сводит repair-логику ревизий 0011 и 0012. Вызывается из миграции 0014 и из
repair_schema.py после restore бэкапа (без смены alembic_version).
"""
from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from app.config import settings

SCHEMA = settings.db_schema

PRODUCT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("id_user_created", sa.Integer()),
    ("datetime_created", sa.DateTime(timezone=True)),
    ("first_reminder_days", sa.SmallInteger()),
    ("second_reminder_days", sa.SmallInteger()),
    ("expires_in", sa.SmallInteger()),
    ("id_storage_place", sa.Integer()),
)

UGP_FIRST_REMINDER: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("first_reminder_shown", sa.DateTime(timezone=True)),
    ("first_reminder_seen", sa.DateTime(timezone=True)),
)

UGP_SECOND_REMINDER: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("second_reminder_shown", sa.DateTime(timezone=True)),
    ("second_reminder_seen", sa.DateTime(timezone=True)),
)

UGP_BASELINE_EXTRA: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("price", sa.Numeric()),
)

ID_TABLES: tuple[tuple[str, str], ...] = (
    ("user", f'"{SCHEMA}"."user"'),
    ("user_group", f'"{SCHEMA}".user_group'),
    ("user_group_user", f'"{SCHEMA}".user_group_user'),
    ("created_user", f'"{SCHEMA}".created_user'),
    ("login_attempt", f'"{SCHEMA}".login_attempt'),
)


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer(), sa.Identity(always=False), primary_key=True)


def _as_sql(op: Any) -> bool:
    ctx = op.get_context()
    return bool(getattr(ctx, "as_sql", False))


def _table_columns(op: Any, table: str) -> dict[str, sa.types.TypeEngine] | None:
    if _as_sql(op):
        return None
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table, schema=SCHEMA):
        return {}
    return {
        column["name"]: column["type"]
        for column in inspector.get_columns(table, schema=SCHEMA)
    }


def _table_exists(op: Any, name: str) -> bool | None:
    if _as_sql(op):
        return None
    return sa.inspect(op.get_bind()).has_table(name, schema=SCHEMA)


def _add_columns(
    op: Any,
    table: str,
    columns: tuple[tuple[str, sa.types.TypeEngine], ...],
    existing: dict[str, sa.types.TypeEngine] | None,
) -> None:
    if existing is None:
        return
    for name, type_ in columns:
        if name not in existing:
            op.add_column(table, sa.Column(name, type_), schema=SCHEMA)


def _normalize_product(op: Any, existing: dict[str, sa.types.TypeEngine]) -> None:
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


def _id_has_default(op: Any, table: str) -> bool | None:
    if _as_sql(op):
        return None
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table, schema=SCHEMA):
        return None
    id_col = next(
        (
            column
            for column in inspector.get_columns(table, schema=SCHEMA)
            if column["name"] == "id"
        ),
        None,
    )
    if id_col is None:
        return None
    if id_col.get("identity"):
        return True
    return bool(id_col.get("default"))


def _ensure_id_sequence(op: Any, table: str, qualified: str) -> None:
    if _id_has_default(op, table):
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


def _repair_columns_and_tables(op: Any) -> None:
    product_cols = _table_columns(op, "product")
    if product_cols is not None and product_cols:
        _normalize_product(op, product_cols)
        _add_columns(op, "product", PRODUCT_COLUMNS, product_cols)

    ugp_cols = _table_columns(op, "user_group_product")
    if ugp_cols is not None and ugp_cols:
        _add_columns(op, "user_group_product", UGP_BASELINE_EXTRA, ugp_cols)
        _add_columns(op, "user_group_product", UGP_FIRST_REMINDER, ugp_cols)
        _add_columns(op, "user_group_product", UGP_SECOND_REMINDER, ugp_cols)

    if _table_exists(op, "feedback") is not True:
        op.create_table(
            "feedback",
            _id(),
            sa.Column("id_user", sa.Integer(), nullable=False),
            sa.Column("datetime_created", sa.DateTime(), nullable=False),
            sa.Column("feedback_text", sa.Text()),
            schema=SCHEMA,
        )

    if _table_exists(op, "feedback_item") is not True:
        op.create_table(
            "feedback_item",
            _id(),
            sa.Column("id_feedback", sa.Integer(), nullable=False),
            sa.Column("item", sa.LargeBinary(), nullable=False),
            schema=SCHEMA,
        )

    if _table_exists(op, "news") is not True:
        op.create_table(
            "news",
            _id(),
            sa.Column("id_user_created", sa.Integer(), nullable=False),
            sa.Column("datetime_created", sa.DateTime(timezone=True), nullable=False),
            sa.Column("header", sa.String(1024), nullable=False),
            sa.Column("body", sa.Text()),
            schema=SCHEMA,
        )

    if _table_exists(op, "user_news_seen") is not True:
        op.create_table(
            "user_news_seen",
            _id(),
            sa.Column("id_news", sa.Integer(), nullable=False),
            sa.Column("id_user_seen", sa.Integer(), nullable=False),
            sa.Column("datetime_seen", sa.DateTime(timezone=True), nullable=False),
            schema=SCHEMA,
        )

    personal_cols = _table_columns(op, "personal_news")
    if personal_cols is not None and personal_cols and "id_feedback" not in personal_cols:
        op.drop_table("personal_news", schema=SCHEMA)
        personal_cols = {}
    if personal_cols is not None and not personal_cols:
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

    user_cols = _table_columns(op, "user")
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

    if _table_exists(op, "news_update") is not True:
        op.create_table(
            "news_update",
            _id(),
            sa.Column("id_user_updated", sa.Integer(), nullable=False),
            sa.Column("datetime_updated", sa.DateTime(timezone=True), nullable=False),
            schema=SCHEMA,
        )

    news_cols = _table_columns(op, "news")
    if news_cols is not None and news_cols and "is_deleted" not in news_cols:
        op.add_column("news", sa.Column("is_deleted", sa.Boolean()), schema=SCHEMA)
    if news_cols is not None and news_cols:
        op.execute(
            sa.text(f'UPDATE "{SCHEMA}".news SET is_deleted = false WHERE is_deleted IS NULL')
        )

    feedback_cols = _table_columns(op, "feedback")
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


def _repair_baseline(op: Any) -> None:
    if _table_exists(op, "created_user") is not True:
        op.create_table(
            "created_user",
            _id(),
            sa.Column("login", sa.String(512)),
            sa.Column("date_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("user_agent", sa.String(512), nullable=False),
            sa.Column("ip", sa.String(256), nullable=False),
            schema=SCHEMA,
        )

    if _table_exists(op, "login_attempt") is not True:
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
        _ensure_id_sequence(op, table, qualified)


def apply_schema_repairs(op: Any) -> None:
    """Добавляет отсутствующие колонки/таблицы и sequence для id."""
    _repair_columns_and_tables(op)
    _repair_baseline(op)
