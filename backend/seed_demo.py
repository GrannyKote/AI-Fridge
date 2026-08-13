"""Наполняет кладовую демо-продуктами.

Использование:
    python seed_demo.py                      # пользователь demo / demo123
    python seed_demo.py --login ivan         # для существующего пользователя
"""

import argparse
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Product, ProductCategory, UnitOfMeasurement, UserGroupProduct
from app.services import users

UNITS = ["шт", "г", "кг", "мл", "л"]

# (название, категория, количество, единица, дней до конца срока годности)
DEMO_PRODUCTS = [
    ("Кефир 2.5%", "Молочные", "0.5", "л", -3),
    ("Молоко 2.5%", "Молочные", "0.8", "л", -1),
    ("Куриное филе", "Мясо и рыба", "300", "г", 1),
    ("Сметана 20%", "Молочные", "150", "г", 2),
    ("Творог 5%", "Молочные", "200", "г", 2),
    ("Фарш говяжий", "Мясо и рыба", "400", "г", 3),
    ("Булочки с кунжутом", "Хлеб и выпечка", "300", "г", 4),
    ("Сыр Гауда", "Молочные", "220", "г", 4),
    ("Хлеб бородинский", "Хлеб и выпечка", "400", "г", 5),
    ("Лосось слабосолёный", "Мясо и рыба", "200", "г", 6),
    ("Йогурт греческий", "Молочные", "480", "г", 8),
    ("Колбаса варёная", "Мясо и рыба", "350", "г", 9),
    ("Яйца С1", "Яйца", "10", "шт", 12),
    ("Перепелиные яйца", "Яйца", "20", "шт", 14),
    ("Масло сливочное", "Молочные", "180", "г", 21),
    ("Кетчуп", "Соусы и специи", "350", "г", 120),
    ("Рис басмати", "Крупы и макароны", "900", "г", 180),
    ("Макароны перья", "Крупы и макароны", "500", "г", 200),
    ("Соус соевый", "Соусы и специи", "250", "мл", 300),
    ("Мука пшеничная", "Крупы и макароны", "2", "кг", 240),
]


def ensure_units(session: Session) -> dict[str, int]:
    existing = {unit.name: unit.id for unit in session.scalars(select(UnitOfMeasurement))}

    for name in UNITS:
        if name not in existing:
            unit = UnitOfMeasurement(name=name)
            session.add(unit)
            session.flush()
            existing[name] = unit.id

    return existing


def ensure_products(session: Session, categories: dict[str, int]) -> dict[str, int]:
    existing = {product.name: product.id for product in session.scalars(select(Product))}

    for name, category, *_ in DEMO_PRODUCTS:
        if name not in existing:
            product = Product(name=name, id_product_category=categories[category])
            session.add(product)
            session.flush()
            existing[name] = product.id

    return existing


def main() -> None:
    parser = argparse.ArgumentParser(description="Демо-данные для кладовой")
    parser.add_argument("--login", default="demo")
    parser.add_argument("--password", default="demo123")
    args = parser.parse_args()

    with Session(engine) as session:
        user = users.find_by_login(session, args.login)

        if user is None:
            user, group = users.create_with_group(session, args.login, args.password)
            print(f"Создан пользователь {user.login} с группой «{group.name}»")
        else:
            groups = users.list_groups(session, user.id)
            if not groups:
                raise SystemExit(f"У пользователя {user.login} нет группы")
            group = groups[0]
            print(f"Используем пользователя {user.login} и группу «{group.name}»")

        categories = {
            category.name: category.id for category in session.scalars(select(ProductCategory))
        }
        missing = {category for _, category, *_ in DEMO_PRODUCTS} - categories.keys()
        if missing:
            raise SystemExit(f"В product_category нет категорий: {', '.join(sorted(missing))}")

        units = ensure_units(session)
        products = ensure_products(session, categories)

        session.execute(
            delete(UserGroupProduct).where(UserGroupProduct.id_user_group == group.id)
        )

        today = date.today()
        for name, category, quantity, unit, days in DEMO_PRODUCTS:
            session.add(
                UserGroupProduct(
                    id_user_group=group.id,
                    id_product=products[name],
                    product_name=name,
                    id_unit_of_measurement=units[unit],
                    quantity=Decimal(quantity),
                    best_before=today + timedelta(days=days),
                    id_product_category=categories[category],
                )
            )

        session.commit()
        print(f"Добавлено продуктов: {len(DEMO_PRODUCTS)}")


if __name__ == "__main__":
    main()
