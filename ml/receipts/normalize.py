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
    Касса, адрес и итог сюда не попадают: их снимает отсев."""
    kept = drop_extra(lines)
    found = analyze(kept)
    matched = [fold(match.raw_line) for match in found if match.raw_line.strip()]
    skipped = [line for line in kept if not any(raw in fold(line) for raw in matched)]
    return to_category(found), skipped
