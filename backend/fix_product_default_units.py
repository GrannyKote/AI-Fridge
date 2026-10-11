"""Заполняет product.id_unit_of_measurement и product.quantity в diplom_all."""

from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Product, ProductCategory, UnitOfMeasurement

UNITS = ("шт", "г", "мл")

# Сначала шт, затем мл; всё остальное — г.
PIECE_PATTERNS = (
    r"\bяйц",
    r"перепелин",
)

ML_PATTERNS = (
    r"\bмолок",
    r"кефир",
    r"ряженк",
    r"простокваш",
    r"айран",
    r"биолакт",
    r"сливк",
    r"\bсок\b",
    r"морс",
    r"компот",
    r"лимонад",
    r"квас",
    r"напиток",
    r"газиров",
    r"минерал",
    r"соус\s+соев",
    r"соевый",
    r"уксус",
    r"сироп",
    r"бальзам",
)


def unit_name_for(name: str, category: str) -> str:
    if category == "Яйца":
        return "шт"

    lowered = name.lower()
    for pattern in PIECE_PATTERNS:
        if re.search(pattern, lowered):
            return "шт"
    for pattern in ML_PATTERNS:
        if re.search(pattern, lowered):
            return "мл"
    return "г"


def quantity_for_unit(unit_name: str) -> Decimal:
    return Decimal("1") if unit_name == "шт" else Decimal("900")


def ensure_units(session: Session) -> dict[str, int]:
    existing = {unit.name: unit.id for unit in session.scalars(select(UnitOfMeasurement))}
    for name in UNITS:
        if name not in existing:
            unit = UnitOfMeasurement(name=name)
            session.add(unit)
            session.flush()
            existing[name] = unit.id
    return existing


def main() -> None:
    with Session(engine) as session:
        units = ensure_units(session)
        categories = {
            row.id: row.name for row in session.scalars(select(ProductCategory)).all()
        }
        products = session.scalars(select(Product)).all()
        by_unit = Counter()
        changes = 0

        for product in products:
            category = categories.get(product.id_product_category, "")
            unit_name = unit_name_for(product.name, category)
            unit_id = units[unit_name]
            quantity = quantity_for_unit(unit_name)
            by_unit[unit_name] += 1

            if (
                product.id_unit_of_measurement != unit_id
                or product.quantity != quantity
            ):
                product.id_unit_of_measurement = unit_id
                product.quantity = quantity
                changes += 1

        session.commit()

        print(f"Всего продуктов: {len(products)}")
        print("Единицы:")
        for name in UNITS:
            print(f"  {name}: {by_unit[name]}")
        print(f"Обновлено записей: {changes}")


if __name__ == "__main__":
    main()
