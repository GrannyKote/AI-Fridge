"""Шаг 3. Строки OCR разбирает модель, имя прижимается к базовому продукту."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from receipts.drop import fold
from receipts.llm import enabled, generate

# Ниже этого косинуса строка ни на одну категорию не похожа.
_MIN_SCORE = 0.45

_PRICE_RE = re.compile(r"\b\d+[.,]\d{2}\b(?!\s*%)")
_WORD_RE = re.compile(r"[а-яё]{3,}")

_override: tuple[str, ...] | None = None
_catalog: tuple[str, ...] = ()
_bases: list[tuple[str, dict[str, float]]] | None = None
_exact_names: dict[str, str] | None = None


@dataclass(frozen=True)
class Match:
    """Что анализ понял в строке, ещё без перевода единиц."""
    raw_line: str
    phrase: str
    category: str
    score: float


def analyze(lines: list[str], complete=None) -> list[Match]:
    """Модель называет продукт по сырой строке. Имя сверяется со списком базовых продуктов.
    Строку, которую модель пропустила, всё равно сверяем по буквам.
    Если модели нет или ответ не JSON, остаётся сравнение по буквам."""
    _prepare(_names())
    lines = [part for line in lines for part in _split_glued(line)]
    reader = complete if complete is not None else (generate if enabled() else None)
    if reader is not None:
        found = _from_llm(lines, reader)
        if found is not None:
            return found
    return [match for line in lines if (match := _match(line)) is not None]


def _from_llm(lines: list[str], complete) -> list[Match] | None:
    if not lines:
        return []
    try:
        parsed = _parse_products(complete(_prompt(lines)))
    except (ValueError, OSError, TypeError, KeyError):
        return None
    if parsed is None:
        return None
    by_index: dict[int, Match] = {}
    for index, product in parsed:
        if index in by_index or not 0 <= index < len(lines):
            continue
        match = _match(lines[index], product)
        if match is not None:
            by_index[index] = match
    for index, line in enumerate(lines):
        if index in by_index:
            continue
        match = _match(line)
        if match is not None:
            by_index[index] = match
    return [by_index[index] for index in sorted(by_index)]


def _split_glued(line: str) -> list[str]:
    """OCR иногда склеивает несколько покупок в одну строку. Режем по базовым именам."""
    folded = fold(line)
    occupied: list[tuple[int, int]] = []
    hits: list[tuple[int, int]] = []
    for name in sorted(_catalog, key=len, reverse=True):
        start = 0
        while True:
            at = folded.find(name, start)
            if at < 0:
                break
            end = at + len(name)
            before = folded[at - 1] if at else " "
            after = folded[end] if end < len(folded) else " "
            overlaps = any(not (end <= left or at >= right) for left, right in occupied)
            if overlaps or before.isalpha() or after.isalpha():
                start = at + 1
                continue
            occupied.append((at, end))
            hits.append((at, end))
            start = end
    if len(hits) < 2:
        return [line]
    hits.sort()
    parts = []
    for index, (start, _end) in enumerate(hits):
        stop = hits[index + 1][0] if index + 1 < len(hits) else len(folded)
        part = line[start:stop].strip(" .,;:-")
        if part:
            parts.append(part)
    return parts or [line]


def _prompt(lines: list[str]) -> str:
    numbered = "\n".join(f"{index}. {line}" for index, line in enumerate(lines))
    return (
        "Пример:\n"
        "0. сэк яблочный восстановленный\n"
        "1. сок блочный\n"
        '[{"i": 0, "product": "яблочный сок"}, {"i": 1, "product": "яблочный сок"}]\n\n'
        f"Строки:\n{numbered}"
    )


def _parse_products(text: str) -> list[tuple[int, str]] | None:
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    found: list[tuple[int, str]] = []
    for item in data:
        if not isinstance(item, dict) or "i" not in item or "product" not in item:
            continue
        product = str(item["product"]).strip()
        if not product:
            continue
        found.append((int(item["i"]), product))
    return found


def _match(line: str, named: str | None = None) -> Match | None:
    """named — имя от модели. Без него сверяется сама строка."""
    phrase = _phrase(line)
    if not phrase:
        return None
    source = named if named else phrase
    exact = _exact(source)
    if exact is not None:
        return Match(raw_line=line.strip(), phrase=phrase, category=exact, score=1.0)
    vector = embed(source)
    if not vector:
        return None
    category, score = _nearest(vector)
    if score < _MIN_SCORE:
        return None
    return Match(raw_line=line.strip(), phrase=phrase, category=category, score=score)


def bind_names(names: tuple[str, ...] | None) -> None:
    """Подмена списка. None снова читает базу, а без неё — файл."""
    global _override, _catalog, _bases, _exact_names
    _override = names
    _catalog = ()
    _bases = None
    _exact_names = None


def _names() -> tuple[str, ...]:
    if _override is not None:
        return _override
    from receipts.products import BASE_PRODUCTS
    from receipts.store import base_product_names

    loaded = base_product_names()
    if loaded:
        return tuple(loaded)
    return BASE_PRODUCTS


def _prepare(names: tuple[str, ...]) -> None:
    global _catalog, _bases, _exact_names
    if _bases is not None and names == _catalog:
        return
    _catalog = names
    _exact_names = {fold(name): name for name in names}
    _bases = [(name, embed(name)) for name in names]


def _exact(text: str) -> str | None:
    if _exact_names is None:
        _prepare(_names())
    return _exact_names.get(fold(text.strip()))


def _phrase(line: str) -> str:
    return re.sub(r"\s+", " ", _PRICE_RE.sub(" ", line)).strip(" .,;:-—*\"'")


def embed(text: str) -> dict[str, float]:
    """Эмбединг строки: частоты буквенных кусков. Общие куски сближают «блочный» и «яблочный»."""
    counts: dict[str, float] = {}
    for word in _WORD_RE.findall(fold(text)):
        padded = f"<{word}>"
        for size in (3, 4):
            if len(padded) < size:
                continue
            for start in range(len(padded) - size + 1):
                gram = padded[start:start + size]
                counts[gram] = counts.get(gram, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in counts.values()))
    if norm == 0:
        return {}
    return {gram: value / norm for gram, value in counts.items()}


def _nearest(vector: dict[str, float]) -> tuple[str, float]:
    best_name = ""
    best_score = -1.0
    for name, base in _base_vectors():
        score = _cosine(vector, base)
        if score > best_score:
            best_name = name
            best_score = score
    return best_name, best_score


def _base_vectors() -> list[tuple[str, dict[str, float]]]:
    if _bases is None:
        _prepare(_names())
    return _bases


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(gram, 0.0) for gram, value in left.items())
