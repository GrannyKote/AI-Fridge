"""JSON той же формы, что POST /products. В кладовую сам ничего не пишет."""

from __future__ import annotations

from receipts.normalize import Item, suggest_storage

# Эти поля обязательны у Марии в PantryItemCreate, чек их не знает.
MISSING = ["category", "unit_id", "best_before", "storage_place_id"]


def to_payload(items: list[Item]) -> dict:
    """Передаем результирующий словарь
    Имя, количество, единицы, хранение.
    Не хватает - категория, номер ед. из бд, срок годности и id хранения"""
    return {
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "storage": suggest_storage(item.name),
                "category": None,
                "unit_id": None,
                "best_before": None, 
                "storage_place_id": None,
            }
            for item in items
        ],
        "missing": list(MISSING),
    }
