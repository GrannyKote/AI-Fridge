"""Шаг 4. Понятый продукт записывается одним именем категории. Единицы — в г, мл, шт."""

from __future__ import annotations

import re
from dataclasses import dataclass

from receipts.products import BASE_PRODUCTS as CATEGORIES

_WORDS = {
    "один": 1, "одна": 1, "одно": 1,
    "два": 2, "две": 2,
    "три": 3, "четыре": 4, "пять": 5,
    "шесть": 6, "семь": 7, "восемь": 8,
    "девять": 9, "десять": 10,
}

# Единица на чеке -> единица кладовой и множитель.
_UNITS = {
    "кг": ("г", 1000),
    "килограмм": ("г", 1000),
    "килограмма": ("г", 1000),
    "килограммов": ("г", 1000),
    "г": ("г", 1),
    "грамм": ("г", 1),
    "грамма": ("г", 1),
    "граммов": ("г", 1),
    "л": ("мл", 1000),
    "литр": ("мл", 1000),
    "литра": ("мл", 1000),
    "литров": ("мл", 1000),
    "мл": ("мл", 1),
    "миллилитр": ("мл", 1),
    "миллилитра": ("мл", 1),
    "миллилитров": ("мл", 1),
    "шт": ("шт", 1),
    "штука": ("шт", 1),
    "штуки": ("шт", 1),
    "штук": ("шт", 1),
}

_UNIT_PATTERN = "|".join(sorted(_UNITS, key=len, reverse=True))
_WORD_PATTERN = "|".join(sorted(_WORDS, key=len, reverse=True))
_QTY_RE = re.compile(
    rf"(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>{_UNIT_PATTERN})\b",
    re.IGNORECASE,
)
_WORD_QTY_RE = re.compile(
    rf"(?P<word>{_WORD_PATTERN})\s+(?P<unit>{_UNIT_PATTERN})\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"\d+(?:[.,]\d+)?\s*%")


@dataclass(frozen=True)
class Item:
    """Продукт после приведения к категории.
    name — имя категории;
    quantity — сколько куплено;
    unit — шт, г или мл;
    raw_line — сырая строка до очистки.
    """
    name: str
    quantity: int | float
    unit: str
    raw_line: str


def to_category(found: list) -> list[Item]:
    """Ближайшая категория становится именем. Килограммы и литры переводятся в г и мл."""
    items: list[Item] = []
    for match in found:
        quantity, unit = _measure(match.phrase)
        name = match.category
        percent = _PERCENT_RE.search(match.phrase)
        if percent:
            name = f"{name} {re.sub(r'\\s+', '', percent.group(0))}"
        items.append(Item(
            name=name,
            quantity=quantity,
            unit=unit,
            raw_line=match.raw_line,
        ))
    return items


def _measure(phrase: str) -> tuple[int | float, str]:
    digit = _QTY_RE.search(phrase)
    word = _WORD_QTY_RE.search(phrase)
    if digit is not None:
        number = float(digit.group("num").replace(",", "."))
        unit, factor = _UNITS[digit.group("unit").lower()]
        return _number(number * factor), unit
    if word is not None:
        number = _WORDS[word.group("word").lower()]
        unit, factor = _UNITS[word.group("unit").lower()]
        return _number(number * factor), unit
    return 1, "шт"


def _number(value: float) -> int | float:
    if value == int(value):
        return int(value)
    return value
