"""Статистика потребления для вкладки «Прогнозы»."""

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    ProductCategory,
    UnitOfMeasurement,
    UserGroupProduct,
    UserGroupProductConsumption,
)

PERIOD_DAYS = {"day": 1, "week": 7, "month": 30, "quarter": 90, "year": 365}

# Полоски на карточке продукта — период, разбитый на равные интервалы.
BUCKETS = 12


def _round(value: float) -> float:
    return round(float(value), 2)


def _fetch(session: Session, group_id: int, since: datetime):
    statement = (
        select(
            UserGroupProductConsumption.quantity,
            UserGroupProductConsumption.date_time,
            UserGroupProduct.product_name,
            UserGroupProduct.id_product_category,
            ProductCategory.name.label("category"),
            UnitOfMeasurement.name.label("unit"),
        )
        .join(
            UserGroupProduct,
            UserGroupProduct.id == UserGroupProductConsumption.id_user_group_product,
        )
        .outerjoin(
            ProductCategory,
            ProductCategory.id == UserGroupProduct.id_product_category,
        )
        .outerjoin(
            UnitOfMeasurement,
            UnitOfMeasurement.id == UserGroupProduct.id_unit_of_measurement,
        )
        .where(
            UserGroupProduct.id_user_group == group_id,
            UserGroupProductConsumption.date_time >= since,
        )
    )

    return session.execute(statement).mappings().all()


def _categories(rows) -> list[dict]:
    totals: dict[tuple[int | None, str], float] = defaultdict(float)
    units: dict[tuple[int | None, str], dict[str | None, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    for row in rows:
        key = (row["id_product_category"], row["category"] or "Без категории")
        quantity = float(row["quantity"])
        totals[key] += quantity
        units[key][row["unit"]] += quantity

    result = []
    for (category_id, name), quantity in totals.items():
        # У категории могут встречаться разные единицы измерения — берём ту,
        # в которой съедено больше всего.
        unit = max(units[(category_id, name)].items(), key=lambda item: item[1])[0]
        result.append(
            {"id": category_id, "name": name, "quantity": _round(quantity), "unit": unit}
        )

    return sorted(result, key=lambda item: item["quantity"], reverse=True)


def _products(rows, start: datetime, period_days: int) -> list[dict]:
    bucket_seconds = period_days * 86_400 / BUCKETS
    products: dict[str, dict] = {}

    for row in rows:
        name = row["product_name"]
        product = products.get(name)

        if product is None:
            product = {
                "name": name,
                "category": row["category"],
                "category_id": row["id_product_category"],
                "unit": row["unit"],
                "entries": 0,
                "total": 0.0,
                "buckets": [0.0] * BUCKETS,
            }
            products[name] = product

        quantity = float(row["quantity"])
        index = int((row["date_time"] - start).total_seconds() / bucket_seconds)
        index = min(max(index, 0), BUCKETS - 1)

        product["entries"] += 1
        product["total"] += quantity
        product["buckets"][index] += quantity

    result = []
    for product in products.values():
        product["per_day"] = _round(product["total"] / period_days)
        product["total"] = _round(product["total"])
        product["buckets"] = [_round(value) for value in product["buckets"]]
        result.append(product)

    return sorted(result, key=lambda item: item["total"], reverse=True)


def consumption(session: Session, group_id: int, period: str) -> dict:
    """Считает потребление за выбранный период: и по категориям, и по продуктам."""
    period_days = PERIOD_DAYS[period]
    start = datetime.now() - timedelta(days=period_days)
    rows = _fetch(session, group_id, start)

    return {
        "period": period,
        "period_days": period_days,
        "categories": _categories(rows),
        "products": _products(rows, start, period_days),
    }
