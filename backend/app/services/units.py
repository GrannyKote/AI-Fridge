"""Normalize comparable quantities without inferring density or piece weight."""

from collections import defaultdict
from decimal import Decimal

UNITS = {"г": "г", "кг": "г", "мл": "мл", "л": "мл", "шт": "шт", "шт.": "шт"}


def normalize_quantity(quantity, unit):
    label = (unit or "").strip().casefold()
    value = Decimal(str(quantity))
    if label in {"кг", "л"}:
        value *= 1000
    return UNITS.get(label, label), value


def aggregate_quantities(operations):
    """Group (product, operation, unit, quantity) by canonical unit."""
    totals = defaultdict(Decimal)
    for product, operation, unit, quantity in operations:
        base, value = normalize_quantity(quantity, unit)
        totals[product, operation, base] += value
    return dict(totals)
