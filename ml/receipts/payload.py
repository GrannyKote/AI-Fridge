"""JSON той же формы, что POST /products. В кладовую сам ничего не пишет."""

from __future__ import annotations

from receipts.normalize import Item, suggest_storage
from receipts.products import pantry_category

# Эти поля обязательны у Марии в PantryItemCreate, чек их не знает.
MISSING = ["unit_id", "best_before", "storage_place_id"]


def to_payload(items: list[Item], skipped: list[str] | None = None) -> dict:
    """Передаем результирующий словарь
    Имя, количество, единицы, хранение.
    Не хватает - категория, номер ед. из бд, срок годности и id хранения"""
    return {
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "storage": item.storage or suggest_storage(item.name),
                "category": pantry_category(item.name),
                "unit_id": None,
                "shelf_life_days": item.shelf_life_days,
                "best_before": None,
                "storage_place_id": None,
            }
            for item in items
        ],
        "skipped": [
            {"line": line, "reason": "не сопоставилось с продуктом"}
            for line in (skipped or [])
        ],
        "missing": list(MISSING),
    }
