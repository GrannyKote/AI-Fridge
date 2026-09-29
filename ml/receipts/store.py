"""Сырой текст и подчищенные строки чека в схему ml. Кладовую не трогает."""

from __future__ import annotations

import os
from pathlib import Path

from receipts.normalize import Item

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.sql"
_DEFAULT_URL = "postgresql://postgres:postgres@127.0.0.1:5432/diplom"


class DatabaseUnavailable(RuntimeError):
    """Postgres не принял соединение. Подчистка при этом уже могла пройти."""


def database_url() -> str:
    raw = os.environ.get("DATABASE_URL", _DEFAULT_URL)
    return raw.replace("postgresql+psycopg://", "postgresql://", 1)


def save_receipt(group_id: int, source: str, raw_text: str, items: list[Item]) -> int:
    if source not in {"photo", "voice"}:
        raise ValueError(f"Неизвестный источник чека: {source}")

    try:
        import psycopg
    except ImportError as exc:
        raise DatabaseUnavailable(
            "Нет пакета psycopg. Запись в ml не сделана."
        ) from exc

    try:
        with psycopg.connect(database_url()) as connection:
            with connection.cursor() as cursor:
                _apply_schema(cursor)
                cursor.execute(
                    """
                    INSERT INTO ml.receipt (id_user_group, source, raw_text)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (group_id, source, raw_text),
                )
                receipt_id = cursor.fetchone()[0]
                cursor.executemany(
                    """
                    INSERT INTO ml.receipt_item
                        (receipt_id, line_no, raw_line, name, quantity, unit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (receipt_id, index, item.raw_line, item.name, item.quantity, item.unit)
                        for index, item in enumerate(items, start=1)
                    ],
                )
            connection.commit()
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable(
            "База недоступна. Подчистка выполнена, запись в ml не сделана."
        ) from exc

    return receipt_id


def base_product_names() -> list[str] | None:
    """Имена из ml.base_product. None — базы нет, и распознавание остаётся на файле."""
    rows = base_products()
    if not rows:
        return None
    return [name for name, _days, _storage in rows]


def base_products() -> list[tuple[str, int | None, str | None]] | None:
    """Имя, срок в днях и место. Пустые поля заполняются один раз и больше не затираются.
    None — базы нет."""
    if not os.environ.get("DATABASE_URL"):
        return None

    try:
        import psycopg
    except ImportError:
        return None

    try:
        with psycopg.connect(database_url(), connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                _apply_schema(cursor)
                _fill_shelf_life(cursor)
                cursor.execute(
                    "SELECT name, shelf_life_days, storage FROM ml.base_product ORDER BY name"
                )
                rows = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
            connection.commit()
    except psycopg.Error:
        return None

    return rows or None


def _fill_shelf_life(cursor) -> None:
    from receipts.normalize import suggest_storage
    from receipts.products import BASE_PRODUCTS, SHELF_LIFE

    rows = [(name, SHELF_LIFE[name], suggest_storage(name)) for name in BASE_PRODUCTS]
    cursor.executemany(
        """
        INSERT INTO ml.base_product (name, shelf_life_days, storage)
        VALUES (%s, %s, %s)
        ON CONFLICT (name) DO NOTHING
        """,
        rows,
    )
    cursor.executemany(
        """
        UPDATE ml.base_product
        SET shelf_life_days = %s
        WHERE name = %s AND shelf_life_days IS NULL
        """,
        [(days, name) for name, days, _storage in rows],
    )
    cursor.executemany(
        """
        UPDATE ml.base_product
        SET storage = %s
        WHERE name = %s AND storage IS NULL
        """,
        [(storage, name) for name, _days, storage in rows],
    )


def _apply_schema(cursor) -> None:
    # psycopg выполняет один оператор за вызов. Файл схемы — несколько CREATE.
    script = _SCHEMA_PATH.read_text(encoding="utf-8")
    for statement in script.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
