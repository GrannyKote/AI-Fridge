"""Shared search implementation for the FastAPI benchmark and quality runner."""
from hashlib import blake2b
from functools import lru_cache

from canonicalization import baseline_prefix, canonical_key, unique_identity

MODES = ("baseline", "hybrid", "pgvector")
BASELINE = r"""
SELECT id, name FROM catalog_eval.product
WHERE lower(name) LIKE %s ESCAPE '\'
ORDER BY name, id LIMIT 5
"""
HYBRID = """
WITH exact AS MATERIALIZED (
    SELECT id FROM catalog_eval.product WHERE key = %(q)s ORDER BY id LIMIT 5
), trgm AS MATERIALIZED (
    SELECT id, row_number() OVER (ORDER BY distance, id) AS rank FROM (
        SELECT id, key <-> %(q)s AS distance FROM catalog_eval.product
        WHERE key %% %(q)s AND NOT EXISTS (SELECT FROM exact)
        ORDER BY key <-> %(q)s LIMIT 64
    ) candidates
), fts AS MATERIALIZED (
    SELECT id, row_number() OVER (ORDER BY score DESC, id) AS rank FROM (
        SELECT id, ts_rank_cd(document, plainto_tsquery('russian', %(q)s)) AS score
        FROM catalog_eval.product WHERE document @@ plainto_tsquery('russian', %(q)s)
        AND NOT EXISTS (SELECT FROM exact)
        ORDER BY score DESC, id LIMIT 64
    ) candidates
), ranked AS (
    SELECT id, 1.0 AS score FROM exact
    UNION ALL SELECT id, 1.0 / (60 + rank) FROM trgm
    UNION ALL SELECT id, 1.0 / (60 + rank) FROM fts
)
SELECT product.id, product.name, top.score FROM (
    SELECT id, sum(score) AS score FROM ranked GROUP BY id
    ORDER BY score DESC, id LIMIT 5
) top JOIN catalog_eval.product USING (id)
ORDER BY top.score DESC, product.id
"""
VECTOR = """
SELECT id, name, 1 - (embedding <=> %(v)s::vector) AS score
FROM catalog_eval.product ORDER BY embedding <=> %(v)s::vector LIMIT 5
"""


@lru_cache(maxsize=8192)
def feature_slot(feature):
    value = int.from_bytes(blake2b(feature.encode(), digest_size=2).digest(), "little")
    return value % 128, 1 if value & 128 else -1


def embedding(text):
    vector = [0] * 128
    for token in text.split():
        padded = f"^{token}$"
        for length in (2, 3, 4):
            for pos in range(len(padded) - length + 1):
                index, sign = feature_slot(padded[pos:pos + length])
                vector[index] += sign
    if not any(vector):
        vector[0] = 1
    return "[" + ",".join(map(str, vector)) + "]"


def suggest(conn, mode, name):
    if mode == "baseline":
        return conn.execute(BASELINE, (baseline_prefix(name),)).fetchall()
    key = canonical_key(name)
    if not key:
        return []
    if mode == "hybrid":
        return conn.execute(HYBRID, {"q": key}).fetchall()
    if mode == "pgvector":
        return conn.execute(VECTOR, {"v": embedding(key)}).fetchall()
    raise ValueError(mode)


def identity(conn, mode, name, suggestions):
    if mode == "baseline":
        rows = conn.execute(
            "SELECT id FROM catalog_eval.product WHERE lower(name) = %s ORDER BY id LIMIT 2",
            (name.strip().lower(),),
        ).fetchall()
    else:
        key = canonical_key(name)
        if not key:
            return None
        rows = conn.execute(
            "SELECT id FROM catalog_eval.product WHERE key = %s ORDER BY id LIMIT 2", (key,),
        ).fetchall()
    if rows:
        return unique_identity([row[0] for row in rows])
    if mode == "pgvector" and len(suggestions) >= 2:
        first, second = suggestions[:2]
        if first[2] >= .90 and first[2] - second[2] >= .06:
            return first[0]
    return None
