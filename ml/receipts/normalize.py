"""Сырые строки проходят отсев, анализ и приведение к категории."""

from __future__ import annotations

from receipts.analyze import analyze
from receipts.category import Item, to_category
from receipts.drop import drop_extra, fold

# Первое совпадение побеждает: «морожен» раньше «молок», «кури» раньше общего холодильника.
_STORAGE = (
    ("Морозилка", ("фарш", "пельмен", "морожен", "замороз", "вареник", "кури", "филе")),
    ("Консервы", ("консерв", "тушен", "сгущен")),
    ("Бакалея", ("подсолнеч", "растител", "мука", "рис", "макарон", "греч", "круп", "сахар", "овсян", "пшено", "горох", "фасол")),
    ("Специи", ("соус", "кетчуп", "спец", "перец", "соль", "уксус", "майонез", "горчиц")),
    ("Холодильник", ("молок", "кефир", "сметан", "творог", "йогурт", "сыр", "яйц", "колбас", "сосиск", "масло", "лосос", "рыб", "мяс")),
    ("Шкаф", ("хлеб", "батон", "булк", "печен")),
)


def suggest_storage(name: str) -> str:
    """Функция возвращает место хранения
    Если такого нет, то возвращает шкаф
    На входе - name - продукт - str
    На выходе - place - место хранения - str"""
    folded = name.lower().replace("ё", "е")
    for place, keys in _STORAGE:
        if any(key in folded for key in keys):
            return place
    return "Шкаф"


def normalize_lines(lines: list[str]) -> list[Item]:
    """Отсев, затем эмбединг, затем одно имя категории.
    На вход - сырые строки - list[str]
    На выходе - список продуктов - list[Item]"""
    items, _skipped = read_products(lines)
    return items


def read_products(lines: list[str]) -> tuple[list[Item], list[str]]:
    """Продукты и строки, которые остались покупками, но не сопоставились.
    Касса, адрес и итог сюда не попадают: их снимает отсев.
    Строка, которую уже поправили вручную, берётся из разметки до сравнения векторов."""
    kept = drop_extra(lines)
    known = line_labels()
    labeled, rest = apply_known_labels(kept, known, _label_catalog() if known else None)
    found = analyze(rest)
    matched = [fold(item.raw_line) for item in labeled if item.raw_line.strip()]
    matched.extend(fold(match.raw_line) for match in found if match.raw_line.strip())
    skipped = [line for line in kept if not any(raw in fold(line) for raw in matched)]
    return labeled + to_category(found), skipped


def apply_known_labels(lines, labels, catalog=None):
    """Уже размеченная строка становится продуктом. Остальные идут дальше как были."""
    items: list[Item] = []
    rest: list[str] = []
    for line in lines:
        label = labels.get(fold(line))
        if label is None:
            rest.append(line)
            continue
        name, quantity, unit, category = label
        days, place = (None, None)
        if catalog is not None:
            days, place = catalog.get(name, (None, None))
        items.append(Item(
            name=name,
            quantity=quantity,
            unit=unit,
            raw_line=line,
            shelf_life_days=days,
            storage=place or suggest_storage(name),
            category=category,
            score=1.0,
        ))
    return items, rest


def _label_catalog():
    from receipts.store import base_products

    loaded = base_products()
    if not loaded:
        return None
    return {name: (days, place) for name, days, place in loaded}


def line_labels():
    from receipts.store import line_labels as load_labels

    return load_labels()
