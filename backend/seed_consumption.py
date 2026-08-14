"""Генерирует историю потребления и списаний за последние 90 дней.

Каждая «покупка» — закрытая строка user_group_product: съеденная целиком
(is_consumed, is_over) или выброшенная целиком (is_wasted, is_over). Такие строки
не видны в кладовой, но дают данные для вкладки «Потребление».

Использование:
    python seed_consumption.py                # пользователь demo
    python seed_consumption.py --login ivan
"""

import argparse
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (
    Product,
    ProductCategory,
    UnitOfMeasurement,
    UserGroupProduct,
    UserGroupProductConsumption,
    UserGroupProductWaste,
)
from app.services import storage, users

WINDOW_DAYS = 90

# (название, категория, единица, размер упаковки, покупок за 90 дней,
#  записей на упаковку, срок годности в днях)
CONSUMPTION = [
    ("Молоко 2.5%", "Молочные", "мл", "1000", 12, 3, 7),
    ("Кефир 2.5%", "Молочные", "мл", "500", 8, 2, 7),
    ("Сметана 20%", "Молочные", "г", "300", 5, 3, 14),
    ("Масло сливочное", "Молочные", "г", "180", 6, 5, 30),
    ("Куриное филе", "Мясо и рыба", "г", "700", 6, 2, 5),
    ("Фарш говяжий", "Мясо и рыба", "г", "500", 4, 2, 5),
    ("Рис басмати", "Крупы и макароны", "г", "900", 3, 4, 365),
    ("Гречка ядрица", "Крупы и макароны", "г", "800", 3, 4, 365),
    ("Макароны перья", "Крупы и макароны", "г", "500", 3, 3, 365),
    ("Яйца С1", "Яйца", "шт", "10", 6, 5, 30),
    ("Хлеб бородинский", "Хлеб и выпечка", "г", "400", 8, 2, 4),
    ("Кетчуп", "Соусы и специи", "г", "350", 2, 6, 180),
    ("Соус соевый", "Соусы и специи", "мл", "250", 2, 5, 365),
]

# Испорченного заметно меньше, чем съеденного.
WASTE = [
    ("Кефир 2.5%", "Молочные", "мл", "500", 4, 1, 7),
    ("Творог 5%", "Молочные", "г", "200", 3, 1, 5),
    ("Сметана 20%", "Молочные", "г", "300", 2, 2, 14),
    ("Хлеб бородинский", "Хлеб и выпечка", "г", "400", 4, 1, 4),
    ("Куриное филе", "Мясо и рыба", "г", "300", 2, 1, 5),
    ("Йогурт греческий", "Молочные", "г", "480", 2, 1, 8),
    ("Кетчуп", "Соусы и специи", "г", "350", 1, 1, 180),
]


def split_pack(quantity: Decimal, parts: int) -> list[Decimal]:
    """Делит упаковку на неравные порции, сумма которых равна упаковке."""
    weights = [random.uniform(0.6, 1.4) for _ in range(parts)]
    total = sum(weights)
    portions = [
        (quantity * Decimal(str(weight / total))).quantize(Decimal("0.01"))
        for weight in weights[:-1]
    ]
    portions.append(quantity - sum(portions))

    return portions


def reference(session: Session, categories: dict[str, int]) -> tuple[dict, dict]:
    units = {unit.name: unit.id for unit in session.scalars(select(UnitOfMeasurement))}
    products = {product.name: product.id for product in session.scalars(select(Product))}

    for name, category, unit, *_ in CONSUMPTION + WASTE:
        if unit not in units:
            raise SystemExit(f"В unit_of_measurement нет единицы «{unit}»")

        if name not in products:
            product = Product(name=name, id_product_category=categories[category])
            session.add(product)
            session.flush()
            products[name] = product.id

    return units, products


def clear_history(session: Session, group_id: int) -> None:
    """Удаляет ранее сгенерированную историю: полностью закрытые строки."""
    closed = select(UserGroupProduct.id).where(
        UserGroupProduct.id_user_group == group_id,
        UserGroupProduct.is_over.is_(True),
        or_(
            UserGroupProduct.is_consumed.is_(True),
            UserGroupProduct.is_wasted.is_(True),
        ),
    )

    for model in (UserGroupProductConsumption, UserGroupProductWaste):
        session.execute(delete(model).where(model.id_user_group_product.in_(closed)))

    session.execute(delete(UserGroupProduct).where(UserGroupProduct.id.in_(closed)))
    session.flush()


def generate(session: Session, group_id: int, plan, model, flags: dict, refs, now) -> int:
    """Создаёт закрытые строки кладовой и записи списания к ним."""
    units, products, categories = refs
    entries = 0

    for name, category, unit, pack, purchases, per_pack, shelf in plan:
        quantity = Decimal(pack)
        step = WINDOW_DAYS / purchases

        # Упаковку расходуют до следующей покупки, но не дольше срока годности.
        span = min(shelf, step)

        for index in range(purchases):
            # Отсчитываем от даты, когда упаковка закончилась: так последняя
            # покупка закрывается сегодня и ни одна запись не попадает в будущее.
            finished = WINDOW_DAYS - step * (index + 1) + random.uniform(0, step / 4)
            bought = now - timedelta(days=max(finished, 0.1) + span)

            item = UserGroupProduct(
                id_user_group=group_id,
                id_product=products[name],
                product_name=name,
                id_unit_of_measurement=units[unit],
                quantity=quantity,
                best_before=(bought + timedelta(days=shelf)).date(),
                id_product_category=categories[category],
                id_storage_place=storage.place_id_for(session, name, category),
                **flags,
            )
            session.add(item)
            session.flush()

            for offset, portion in enumerate(split_pack(quantity, per_pack)):
                moment = bought + timedelta(
                    days=span * (offset + random.uniform(0.2, 0.9)) / per_pack,
                    hours=random.uniform(0, 12),
                )
                session.add(
                    model(
                        id_user_group_product=item.id,
                        quantity=portion,
                        date_time=moment,
                    )
                )
                entries += 1

    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="История потребления и списаний для демо")
    parser.add_argument("--login", default="demo")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    random.seed(args.seed)

    with Session(engine) as session:
        user = users.find_by_login(session, args.login)
        if user is None:
            raise SystemExit(f"Пользователь {args.login} не найден")

        groups = users.list_groups(session, user.id)
        if not groups:
            raise SystemExit(f"У пользователя {args.login} нет группы")
        group = groups[0]

        categories = {
            category.name: category.id for category in session.scalars(select(ProductCategory))
        }
        missing = {category for _, category, *_ in CONSUMPTION + WASTE} - categories.keys()
        if missing:
            raise SystemExit(f"В product_category нет категорий: {', '.join(sorted(missing))}")

        units, products = reference(session, categories)
        refs = (units, products, categories)
        clear_history(session, group.id)

        now = datetime.now()
        eaten = generate(
            session,
            group.id,
            CONSUMPTION,
            UserGroupProductConsumption,
            {"is_consumed": True, "is_over": True},
            refs,
            now,
        )
        wasted = generate(
            session,
            group.id,
            WASTE,
            UserGroupProductWaste,
            {"is_wasted": True, "is_over": True},
            refs,
            now,
        )

        session.commit()
        print(f"Группа «{group.name}»: потребление — {eaten}, списания — {wasted}")


if __name__ == "__main__":
    main()
