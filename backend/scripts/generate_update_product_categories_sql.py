"""Генерирует update_product_categories.sql из текущей БД (POSTGRES_* / DATABASE_URL)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.database import engine

OUT_BY_NAME = Path(__file__).with_name("update_product_categories.sql")
OUT_BY_ID = Path(__file__).with_name("update_product_categories_by_id.sql")

QUERY = text(
    """
    SELECT p.id, p.id_product_category, pc.name
    FROM diplom_all.product p
    JOIN diplom_all.product_category pc ON pc.id = p.id_product_category
    ORDER BY p.id
    """
)


def main() -> None:
    with engine.connect() as conn:
        rows = conn.execute(QUERY).all()

    lines = [
        "-- Обновление diplom_all.product.id_product_category по product.id",
        "-- id категории берётся из product_category.name (порядок id в справочнике может отличаться).",
        "",
        "BEGIN;",
        "",
        "UPDATE diplom_all.product AS p",
        "SET id_product_category = pc.id",
        "FROM (",
        "  VALUES",
    ]

    for index, (product_id, _category_id, category_name) in enumerate(rows):
        escaped = category_name.replace("'", "''")
        suffix = "," if index < len(rows) - 1 else ""
        lines.append(f"    ({product_id}, '{escaped}'){suffix}")

    lines.extend(
        [
            ") AS mapping(product_id, category_name)",
            "JOIN diplom_all.product_category AS pc ON pc.name = mapping.category_name",
            "WHERE p.id = mapping.product_id;",
            "",
            "COMMIT;",
            "",
        ]
    )

    OUT_BY_NAME.write_text("\n".join(lines), encoding="utf-8")

    id_lines = [
        "-- Прямое обновление id_product_category (325 product.id).",
        "-- Используйте только если id в product_category совпадают с эталоном:",
        "--   1 Молочные, 2 Крупы и макароны, 3 Мясо и рыба,",
        "--   4 Соусы и специи, 5 Яйца, 6 Хлеб и выпечка",
        "-- Иначе — update_product_categories.sql (по имени категории).",
        "",
        "BEGIN;",
        "",
        "UPDATE diplom_all.product AS p",
        "SET id_product_category = mapping.id_product_category",
        "FROM (",
        "  VALUES",
    ]
    for index, (product_id, category_id, _name) in enumerate(rows):
        suffix = "," if index < len(rows) - 1 else ""
        id_lines.append(f"    ({product_id}, {category_id}){suffix}")
    id_lines.extend(
        [
            ") AS mapping(product_id, id_product_category)",
            "WHERE p.id = mapping.product_id;",
            "",
            "COMMIT;",
            "",
        ]
    )
    OUT_BY_ID.write_text("\n".join(id_lines), encoding="utf-8")

    print(f"Записано {len(rows)} строк в {OUT_BY_NAME.name} и {OUT_BY_ID.name}")


if __name__ == "__main__":
    main()
