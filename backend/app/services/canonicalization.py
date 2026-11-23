"""Catalog search and conservative reuse of an unambiguous canonical key."""

import re
import unicodedata

ALIASES = {
    "сырок": "творожок", "сгущ": "сгущенка", "йог": "йогурт",
    "газвода": "газировка", "кеф": "кефир", "твор": "творог", "мол": "молоко",
    "смет": "сметана", "шокол": "шоколад", "печ": "печенье", "колб": "колбаса",
}
BRANDS = ("добрый", "простоквашино", "домик в деревне", "чудо")
PACK = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:кг|г|мл|л|шт)\b")
PERCENT = re.compile(r"(\d+)(?:[.,](\d+))?\s*%")


def canonical_key(name):
    name = unicodedata.normalize("NFKC", name).casefold().replace("ё", "е")
    name = PERCENT.sub(lambda m: m[1] + "доля" + (m[2] or "").rstrip("0"), name)
    name = PACK.sub(" ", name)
    for brand in BRANDS:
        name = re.sub(r'["«]\s*' + brand + r'\s*["»]', " ", name)
    tokens = re.findall(r"[^\W_]+", name)
    return " ".join(sorted(ALIASES.get(token, token) for token in tokens))


def baseline_prefix(name):
    prefix = name.strip().lower()
    for char in ("\\", "%", "_"):
        prefix = prefix.replace(char, "\\" + char)
    return prefix + "%"


def unique_identity(ids):
    return ids[0] if len(ids) == 1 else None
