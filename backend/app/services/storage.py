"""Подбор места хранения для строки кладовой."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import StoragePlace

# Сначала смотрим на конкретный продукт, иначе — на категорию.
BY_NAME = {
    "Фарш говяжий": "Морозилка",
    "Куриное филе": "Морозилка",
}

BY_CATEGORY = {
    "Молочные": "Холодильник",
    "Яйца": "Холодильник",
    "Мясо и рыба": "Холодильник",
    "Хлеб и выпечка": "Шкаф",
    "Крупы и макароны": "Бакалея",
    "Соусы и специи": "Специи",
}

DEFAULT_PLACE = "Шкаф"


def _places(session: Session) -> dict[str, int]:
    return {place.name: place.id for place in session.scalars(select(StoragePlace))}


def place_id_for(session: Session, name: str, category: str | None) -> int:
    places = _places(session)
    wanted = BY_NAME.get(name) or BY_CATEGORY.get(category or "") or DEFAULT_PLACE
    place_id = places.get(wanted) or places.get(DEFAULT_PLACE)

    if place_id is None:
        raise ValueError("В storage_place нет мест хранения")

    return place_id
