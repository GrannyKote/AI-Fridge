"""Пересчитывает id_product_category в diplom_all.product по названию."""

from __future__ import annotations

import re
from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Product, ProductCategory

# Порядок важен: более специфичные правила выше.
RULES: list[tuple[str, list[str]]] = [
    (
        "Яйца",
        [
            r"\bяйц",
            r"перепелин",
        ],
    ),
    (
        "Хлеб и выпечка",
        [
            r"\bхлеб\b",
            r"батон",
            r"булоч",
            r"багет",
            r"лаваш",
            r"круассан",
            r"сдоб",
        ],
    ),
    (
        "Соусы и специи",
        [
            r"кетчуп",
            r"майонез",
            r"горчица",
            r"аджика",
            r"соус\b",
            r"соевый",
            r"\bсоль\b",
            r"сахар",
            r"дрожж",
            r"крахмал",
            r"приправ",
            r"специ",
            r"уксус",
            r"масло\s+(оливков|подсолнеч|расторопш)",
        ],
    ),
    (
        "Молочные",
        [
            r"\bмолок",
            r"кефир",
            r"ряженк",
            r"сметан",
            r"творог",
            r"йогурт",
            r"простокваш",
            r"айран",
            r"биолакт",
            r"сливк",
            r"\bсыр\b",
            r"сыр[\s-]",
            r"сырок\s",
            r"сырн",
            r"масло\s+слив",
            r"масло\s+топл",
            r"сгущ",
            r"творожн",
        ],
    ),
    (
        "Мясо и рыба",
        [
            r"курин",
            r"индей",
            r"говяж",
            r"говядин",
            r"свин",
            r"баранин",
            r"телят",
            r"утк",
            r"гус",
            r"кролик",
            r"фарш",
            r"стейк",
            r"эскалоп",
            r"ребр",
            r"окороч",
            r"крыл",
            r"бёдр",
            r"грудк",
            r"филе",
            r"тушк",
            r"печень",
            r"сердечк",
            r"язык\b",
            r"колбас",
            r"сосиск",
            r"сардель",
            r"ветчин",
            r"бекон",
            r"сало\b",
            r"сервелат",
            r"salami",
            r"салami",
            r"копчен",
            r"форель",
            r"с[её]мг",
            r"лосос",
            r"горбуш",
            r"минтай",
            r"треск",
            r"судак",
            r"щук",
            r"карп\b",
            r"сом\b",
            r"окун",
            r"пангаси",
            r"кальмар",
            r"кревет",
            r"мидии",
            r"крабов",
            r"икра\b",
            r"сельд",
            r"скумбри",
            r"кильк",
            r"тунец",
            r"шпрот",
            r"туш[её]нк",
            r"наггетс",
            r"котлет",
            r"пельмен",
            r"вареник",
            r"голубц",
            r"барбекю",
            r"колбаск",
        ],
    ),
    (
        "Крупы и макароны",
        [
            r"\bрис\b",
            r"греч",
            r"макарон",
            r"\bмук",
            r"овсян",
            r"пшено",
            r"перлов",
            r"ячн",
            r"кукурузн",
            r"манн",
            r"булгур",
            r"киноа",
            r"кускус",
            r"полб",
            r"чечевиц",
            r"фасол",
            r"горох",
            r"\bнут\b",
            r"соя\s+в",
            r"лапш",
            r"смесь\s+(для|круп)",
            r"\bкруп",
        ],
    ),
]


def category_for_name(name: str) -> str:
    lowered = name.strip().lower()
    for category, patterns in RULES:
        for pattern in patterns:
            if re.search(pattern, lowered):
                return category
    return "Крупы и макароны"


def main() -> None:
    with Session(engine) as session:
        categories = {
            row.name: row.id
            for row in session.scalars(select(ProductCategory)).all()
        }
        missing = {name for name, _ in RULES} - categories.keys()
        if missing:
            raise SystemExit(f"Нет категорий в product_category: {', '.join(sorted(missing))}")

        products = session.scalars(select(Product)).all()
        changes: list[tuple[int, str, str, str]] = []
        after = Counter()

        for product in products:
            wanted = category_for_name(product.name)
            after[wanted] += 1
            current = next(
                (name for name, cid in categories.items() if cid == product.id_product_category),
                "?",
            )
            if product.id_product_category != categories[wanted]:
                changes.append((product.id, product.name, current, wanted))
                product.id_product_category = categories[wanted]

        session.commit()

        print(f"Всего продуктов: {len(products)}")
        print("После пересчёта:")
        for name, count in after.most_common():
            print(f"  {name}: {count}")
        print(f"Изменено записей: {len(changes)}")
        for pid, name, old, new in changes:
            print(f"  [{pid}] {name}: {old} -> {new}")


if __name__ == "__main__":
    main()
