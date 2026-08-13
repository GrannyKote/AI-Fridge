"""Статистика потребления и списаний для вкладки «Прогнозы»."""

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    ProductCategory,
    UnitOfMeasurement,
    UserGroupProduct,
    UserGroupProductConsumption,
    UserGroupProductWaste,
)

PERIOD_DAYS = {"day": 1, "week": 7, "month": 30, "quarter": 90, "year": 365}

# Полоски на карточке продукта — период, разбитый на равные интервалы.
BUCKETS = 12


def _round(value: float) -> float:
    return round(float(value), 2)


def _fetch(session: Session, model, group_id: int, since: datetime):
    """Читает списания из user_group_product_consumption или ..._waste."""
    statement = (
        select(
            model.quantity,
            model.date_time,
            UserGroupProduct.product_name,
            UserGroupProduct.id_product_category,
            ProductCategory.name.label("category"),
            UnitOfMeasurement.name.label("unit"),
        )
        .join(UserGroupProduct, UserGroupProduct.id == model.id_user_group_product)
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
            model.date_time >= since,
        )
    )

    return session.execute(statement).mappings().all()


def _categories(eaten, wasted) -> list[dict]:
    totals: dict[tuple[int | None, str], dict[str, float]] = defaultdict(
        lambda: {"consumed": 0.0, "wasted": 0.0}
    )
    units: dict[tuple[int | None, str], dict[str | None, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    for rows, key_name in ((eaten, "consumed"), (wasted, "wasted")):
        for row in rows:
            key = (row["id_product_category"], row["category"] or "Без категории")
            quantity = float(row["quantity"])
            totals[key][key_name] += quantity
            units[key][row["unit"]] += quantity

    result = []
    for (category_id, name), amounts in totals.items():
        # У категории могут встречаться разные единицы измерения — берём ту,
        # в которой прошло больше всего.
        unit = max(units[(category_id, name)].items(), key=lambda item: item[1])[0]
        result.append(
            {
                "id": category_id,
                "name": name,
                "unit": unit,
                "consumed": _round(amounts["consumed"]),
                "wasted": _round(amounts["wasted"]),
            }
        )

    return sorted(result, key=lambda item: item["consumed"] + item["wasted"], reverse=True)


def _series(rows, start: datetime, period_days: int) -> dict[str, dict]:
    bucket_seconds = period_days * 86_400 / BUCKETS
    series: dict[str, dict] = {}

    for row in rows:
        name = row["product_name"]
        item = series.get(name)

        if item is None:
            item = {"entries": 0, "total": 0.0, "buckets": [0.0] * BUCKETS}
            series[name] = item

        quantity = float(row["quantity"])
        index = int((row["date_time"] - start).total_seconds() / bucket_seconds)
        index = min(max(index, 0), BUCKETS - 1)

        item["entries"] += 1
        item["total"] += quantity
        item["buckets"][index] += quantity

    for item in series.values():
        item["per_day"] = _round(item["total"] / period_days)
        item["total"] = _round(item["total"])
        item["buckets"] = [_round(value) for value in item["buckets"]]

    return series


def _products(eaten, wasted, start: datetime, period_days: int) -> list[dict]:
    consumption = _series(eaten, start, period_days)
    waste = _series(wasted, start, period_days)
    view: dict[str, dict] = {}

    for rows in (eaten, wasted):
        for row in rows:
            name = row["product_name"]

            if name not in view:
                view[name] = {
                    "name": name,
                    "category": row["category"],
                    "category_id": row["id_product_category"],
                    "unit": row["unit"],
                    "consumption": consumption.get(name),
                    "waste": waste.get(name),
                }

    return sorted(
        view.values(),
        key=lambda item: (item["consumption"] or {}).get("total", 0)
        + (item["waste"] or {}).get("total", 0),
        reverse=True,
    )


def usage(session: Session, group_id: int, period: str) -> dict:
    """Считает потребление и списания за выбранный период."""
    period_days = PERIOD_DAYS[period]
    start = datetime.now() - timedelta(days=period_days)
    eaten = _fetch(session, UserGroupProductConsumption, group_id, start)
    wasted = _fetch(session, UserGroupProductWaste, group_id, start)

    return {
        "period": period,
        "period_days": period_days,
        "categories": _categories(eaten, wasted),
        "products": _products(eaten, wasted, start, period_days),
    }
