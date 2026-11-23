from canonicalization import canonical_key, baseline_prefix, unique_identity
from dataset import fixture, SPECIAL


def test_dataset_sizes_and_labels():
    catalog, queries = fixture()
    ids = dict(catalog)
    assert len(ids) == len(set(ids.values())) == 1000
    assert len(queries) >= 2000
    assert len({row[1] for row in queries}) == len(queries)
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
