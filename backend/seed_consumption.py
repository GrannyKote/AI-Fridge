"""Генерирует историю потребления за последние 90 дней.

Каждая «покупка» — закрытая строка user_group_product (is_consumed, is_over),
съеденная за несколько записей в user_group_product_consumption. Такие строки
не видны в кладовой, но дают данные для вкладки «Потребление».

Использование:
    python seed_consumption.py                # пользователь demo
    python seed_consumption.py --login ivan
"""

import argparse
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (
    Product,
    ProductCategory,
    UnitOfMeasurement,
    UserGroupProduct,
    UserGroupProductConsumption,
)
from app.services import users

WINDOW_DAYS = 90

# (название, категория, единица, размер упаковки, покупок за 90 дней,
#  записей о потреблении на упаковку, срок годности в днях)
HISTORY = [
    ("Молоко 2.5%", "Молочные", "л", "1", 12, 3, 7),
    ("Кефир 2.5%", "Молочные", "л", "0.5", 8, 2, 7),
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

    for name, category, unit, *_ in HISTORY:
        if unit not in units:
            raise SystemExit(f"В unit_of_measurement нет единицы «{unit}»")

        if name not in products:
            product = Product(name=name, id_product_category=categories[category])
            session.add(product)
            session.flush()
            products[name] = product.id

    return units, products


def main() -> None:
    parser = argparse.ArgumentParser(description="История потребления для демо")
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
        missing = {category for _, category, *_ in HISTORY} - categories.keys()
        if missing:
            raise SystemExit(f"В product_category нет категорий: {', '.join(sorted(missing))}")

        units, products = reference(session, categories)

        # Старую историю удаляем целиком: строки, полностью списанные в потребление.
        closed = select(UserGroupProduct.id).where(
            UserGroupProduct.id_user_group == group.id,
            UserGroupProduct.is_consumed.is_(True),
            UserGroupProduct.is_over.is_(True),
        )
        session.execute(
            delete(UserGroupProductConsumption).where(
                UserGroupProductConsumption.id_user_group_product.in_(closed)
            )
        )
        session.execute(delete(UserGroupProduct).where(UserGroupProduct.id.in_(closed)))
        session.flush()

        now = datetime.now()
        entries = 0

        for name, category, unit, pack, purchases, per_pack, shelf in HISTORY:
            quantity = Decimal(pack)
            step = WINDOW_DAYS / purchases

            # Упаковку съедают до следующей покупки, но не дольше срока годности.
            span = min(shelf, step)

            for index in range(purchases):
                # Отсчитываем от даты, когда упаковка закончилась: так последняя
                # покупка доедается прямо сегодня и ни одна порция не попадает
                # в будущее.
                finished = WINDOW_DAYS - step * (index + 1) + random.uniform(0, step / 4)
                bought = now - timedelta(days=max(finished, 0.1) + span)

                item = UserGroupProduct(
                    id_user_group=group.id,
                    id_product=products[name],
                    product_name=name,
                    id_unit_of_measurement=units[unit],
                    quantity=quantity,
                    best_before=(bought + timedelta(days=shelf)).date(),
                    id_product_category=categories[category],
                    is_consumed=True,
                    is_over=True,
                )
                session.add(item)
                session.flush()

                for offset, portion in enumerate(split_pack(quantity, per_pack)):
                    eaten = bought + timedelta(
                        days=span * (offset + random.uniform(0.2, 0.9)) / per_pack,
                        hours=random.uniform(0, 12),
                    )
                    session.add(
                        UserGroupProductConsumption(
                            id_user_group_product=item.id,
                            quantity=portion,
                            date_time=eaten,
                        )
                    )
                    entries += 1

        session.commit()
        print(f"Добавлено записей о потреблении: {entries} для группы «{group.name}»")


if __name__ == "__main__":
    main()
