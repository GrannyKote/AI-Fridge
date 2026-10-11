"""Подбор места хранения для строки кладовой."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Product, StoragePlace

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


def default_place_id(
    session: Session,
    *,
    product: Product | None,
    name: str,
    category: str | None,
) -> int:
    """product.id_storage_place, иначе эвристика по имени/категории."""
    if product is not None and product.id_storage_place is not None:
        place = session.get(StoragePlace, product.id_storage_place)
        if place is not None:
            return place.id

    return place_id_for(session, name, category)


def resolve_storage_place_id(
    session: Session,
    *,
    product: Product | None,
    name: str,
    category: str | None,
    explicit_id: int | None = None,
) -> int:
    """Явный storage_place_id из запроса или default_place_id."""
    if explicit_id is not None and session.get(StoragePlace, explicit_id) is not None:
        return explicit_id

    return default_place_id(session, product=product, name=name, category=category)
