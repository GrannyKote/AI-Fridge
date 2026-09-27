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


def _apply_schema(cursor) -> None:
    # psycopg выполняет один оператор за вызов. Файл схемы — несколько CREATE.
    script = _SCHEMA_PATH.read_text(encoding="utf-8")
    for statement in script.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
