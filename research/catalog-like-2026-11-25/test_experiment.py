from collections import Counter
from decimal import Decimal

from app.services.canonicalization import canonical_key, baseline_prefix, unique_identity
from app.services.units import aggregate_quantities
from dataset import fixture, SPECIAL


def test_dataset_sizes_and_labels():
    catalog, queries, operations = fixture()
    ids = dict(catalog)
    assert len(ids) == len(set(ids.values())) == 1000
    assert len(queries) >= 2000
    assert len({row[1] for row in queries}) == len(queries)
    assert len(operations) == 25000
    assert Counter(row[4] for row in operations).keys() == {"г", "кг", "л", "мл", "шт"}
    for _, _, target, distractor, novel in queries:
        if target is None:
            assert novel and distractor in ids
        else:
            assert target in ids and target != distractor


def test_distinguishing_attributes_and_aliases():
    assert canonical_key('  МОЛОКО «Домик в деревне» 2.50 % 1 л ') == canonical_key("молоко 2,5%")
    assert canonical_key("Клубника йог") == canonical_key("йогурт клубника")
    for left, right in SPECIAL:
        assert canonical_key(left) != canonical_key(right)
    assert unique_identity([1, 2]) is None
    assert baseline_prefix("Молоко 2,5%") == r"молоко 2,5\%%"


def test_isolation_of_incompatible_units():
    rows = [(1, "consumed", "кг", ".5"), (1, "consumed", "г", "200"),
            (1, "consumed", "мл", "100"), (1, "consumed", "л", ".25"),
            (1, "consumed", "шт.", "2"), (1, "wasted", "г", "13")]
    assert aggregate_quantities(rows) == {
        (1, "consumed", "г"): Decimal(700), (1, "consumed", "мл"): Decimal(350),
        (1, "consumed", "шт"): Decimal(2), (1, "wasted", "г"): Decimal(13),
    }
