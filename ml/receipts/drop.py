"""Шаг 2. Сырые строки чека: лишнее выбрасываем, покупки оставляем как есть."""

from __future__ import annotations

import re

_JUNK = {
    "итог", "итого", "ндс", "сдача", "карта", "инн", "касса",
    "кассир", "кассовый", "чек", "приход", "расход", "смена",
    "ооо", "оао", "зао", "пао", "ип", "ао",
    "фн", "фд", "фп", "фпд", "ккт", "огрн",
    "сайт", "тел", "телефон",
}

_HOMOGLYPHS = str.maketrans({
    "a": "а", "b": "в", "c": "с", "e": "е", "h": "н", "k": "к",
    "m": "м", "o": "о", "p": "р", "t": "т", "x": "х", "y": "у",
})

# Одно короткое слово оставляем, только если это само название продукта.
_SHORT_PRODUCTS = {"чай", "лук", "рис", "сок", "сыр", "мед", "соль"}

_ADDRESS_RE = re.compile(
    r"\b(?:ул|улица|проспект|переулок|шоссе|область|дом)\b",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)
_PRICE_RE = re.compile(r"\b\d+[.,]\d{2}\b(?!\s*%)")


def fold(line: str) -> str:
    return line.lower().replace("ё", "е").translate(_HOMOGLYPHS)


def drop_extra(lines: list[str]) -> list[str]:
    """Касса, адрес, итог и обрывки не идут дальше. Текст покупки не переписывается."""
    kept: list[str] = []
    for line in lines:
        raw = line.strip()
        if raw and _keep(raw):
            kept.append(raw)
    return kept


def _keep(line: str) -> bool:
    folded = fold(line)
    tokens = set(_TOKEN_RE.findall(folded))
    if tokens & _JUNK or _ADDRESS_RE.search(folded):
        return False
    rest = _PRICE_RE.sub(" ", folded)
    # 7113.40 — это цена, её уже сняли. 6841 без копеек — номер дома или кассы.
    if re.search(r"\d{4,}", rest):
        return False
    words = _TOKEN_RE.findall(rest)
    if not words:
        return False
    if len(words) == 1:
        token = words[0]
        if token.isdigit():
            return False
        if len(token) <= 3 and token not in _SHORT_PRODUCTS:
            return False
    return True
