"""Применяет update_product_categories.sql к БД из POSTGRES_* / DATABASE_URL."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import text

from app.database import engine

DEFAULT_SQL = Path(__file__).with_name("update_product_categories.sql")


def main() -> None:
    parser = argparse.ArgumentParser(description="UPDATE diplom_all.product.id_product_category")
    parser.add_argument(
        "--sql",
        type=Path,
        default=DEFAULT_SQL,
        help="SQL-файл (по умолчанию update_product_categories.sql)",
    )
    args = parser.parse_args()

    raw = args.sql.read_text(encoding="utf-8")
    # engine.begin() сам открывает транзакцию — BEGIN/COMMIT из файла убираем.
    body = "\n".join(
        line
        for line in raw.splitlines()
        if line.strip().upper() not in {"BEGIN;", "COMMIT;"}
        and not line.strip().startswith("--")
    )

    with engine.begin() as conn:
        conn.execute(text(body))

    print(f"Применено: {args.sql}")


if __name__ == "__main__":
    main()
