"""Одна подчистка для текста чека с фото и с голоса."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Токен целиком. «карт» как подстрока не трогаем: иначе пропадёт «картофель».
_JUNK = {"итог", "итого", "ндс", "сдача", "карта", "инн", "касса"}

_WORDS = {
    "один": 1,
    "одна": 1,
    "одно": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}

# Единица на чеке -> единица справочника Марии (шт, г, мл) и множитель.
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
_PRICE_RE = re.compile(r"\b\d+[.,]\d{2}\b(?!\s*%)")
_TOKEN_RE = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)


# Первое совпадение побеждает: «морожен» раньше «молок», «кури» раньше общего холодильника.
_STORAGE = (
    ("Морозилка", ("фарш", "пельмен", "морожен", "замороз", "вареник", "кури", "филе")),
    ("Консервы", ("консерв", "тушен", "сгущен")),
    ("Бакалея", ("подсолнеч", "растител", "мука", "рис", "макарон", "греч", "круп", "сахар", "овсян", "пшено", "горох", "фасол")),
    ("Специи", ("соус", "кетчуп", "спец", "перец", "соль", "уксус", "майонез", "горчиц")),
    ("Холодильник", ("молок", "кефир", "сметан", "творог", "йогурт", "сыр", "яйц", "колбас", "сосиск", "масло", "лосос", "рыб", "мяс")),
    ("Шкаф", ("хлеб", "батон", "булк", "печен")),
)


@dataclass(frozen=True)
class Item:
    """Класс для хранения Продукта
    name - Имя;
    quantity - Сколько куплено;
    unit - единица (шт, г и мл)
    raw_line - исходная строка до очистки
    """
    name: str
    quantity: int | float
    unit: str
    raw_line: str


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
    """Превращает сырые строки чека в список продуктов
    На вход - "сырые строки" - list[str]
    На выходе - список продуктов - list[Item]"""
    items: list[Item] = []
    for line in lines:
        item = _parse_line(line)
        if item is not None:
            items.append(item)
    return items



def _is_junk(line: str) -> bool:
    """Скрытая функция проверки наличия токена в исключащем списке
    На вход - строка str
    На выходе - True/False
    True - будем игнорировать эту строку
    False - может быть продукт"""
    tokens = {token.lower() for token in _TOKEN_RE.findall(line)}
    return bool(tokens & _JUNK)


def _parse_line(line: str) -> Item | None:
    """Скрытая функция парсера строки
    На вход - сырая строка - str
    На выходе - Item или None"""
    raw = line.strip()
    #если служебные слова, то игнорируем
    if not raw or _is_junk(raw):
        return None

    quantity = 1
    unit = "шт"
    rest = raw

    #ищем числа
    digit = _QTY_RE.search(rest)
    #ищем слова
    word = _WORD_QTY_RE.search(rest)
    if digit is not None:
        #если нашли число, то меняем запятую, приводим единицы измерения к базе
        #запоминаем результат
        number = float(digit.group("num").replace(",", "."))
        unit, factor = _UNITS[digit.group("unit").lower()]
        quantity = _number(number * factor)
        rest = rest[: digit.start()] + " " + rest[digit.end() :]
    elif word is not None:
        #если нашли текст (два литра), то приводим единицы измерения к базе
        #запоминаем результат
        number = _WORDS[word.group("word").lower()]
        unit, factor = _UNITS[word.group("unit").lower()]
        quantity = _number(number * factor)
        rest = rest[: word.start()] + " " + rest[word.end() :]

    # sub меняет каждое совпадение на пробел. Цена — это 89.90 или 45,00.
    # 2.5% не трогаем: после числа стоит знак процента.
    rest = _PRICE_RE.sub(" ", rest)
    # \s+ схлопывает подряд идущие пробелы в один.
    # strip срезает с краёв пробел, точку, запятую, двоеточие, тире и звёздочку.
    name = re.sub(r"\s+", " ", rest).strip(" .,;:-—*")
    # Пустое имя значит, что в строке была только цена. Такой строке не место в списке.
    if not name:
        return None

    #возвращаем имя, количество, 
    return Item(name=name, quantity=quantity, unit=unit, raw_line=raw)




def _number(value: float) -> int | float:
    """Отрезает нули после запятой, если они остаются"""
    if value == int(value):
        return int(value)
    return value
