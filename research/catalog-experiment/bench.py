"""Run quality evaluation or populate a disposable PostgreSQL benchmark catalog."""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import json
import os
from statistics import mean

import psycopg

from app.services.canonicalization import canonical_key
from app.services.units import aggregate_quantities
from dataset import DATA, ROOT, write_csv
from search import MODES, embedding, identity, suggest, VECTOR

RESULTS = ROOT / "results"
DSN = os.environ.get("CATALOG_DSN", "postgresql://postgres@127.0.0.1:55439/catalog_bench_ru")


def connect():
    conn = psycopg.connect(DSN, autocommit=True)
    conn.execute("SET pg_trgm.similarity_threshold = 0.20")
    conn.execute("SET hnsw.ef_search = 64")
    return conn


def records(path):
    with (DATA / path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def prepare(conn, size, vector):
    if conn.info.dbname not in {"catalog_bench", "catalog_bench_ru"}:
        raise ValueError("Use a disposable catalog_bench or catalog_bench_ru database")
    conn.execute((ROOT / "001_catalog.sql").read_text(encoding="utf-8"))
    if not conn.execute("SELECT cardinality(show_trgm(%s))", ("молоко",)).fetchone()[0]:
        raise RuntimeError("Database LC_CTYPE fails to classify Cyrillic for pg_trgm")
    conn.execute("TRUNCATE catalog_eval.product")
    conn.execute("DROP INDEX IF EXISTS catalog_eval.catalog_eval_hnsw")
    if vector:
        # Build after COPY, so the 100k catalog uses the bulk build path.
        extension, column, _ = (ROOT / "002_vector.sql").read_text(encoding="utf-8").split(";", 2)
        conn.execute(extension)
        conn.execute(column)
    items = records("catalog.csv")
    columns = "id, name, key, embedding" if vector else "id, name, key"
    with conn.cursor().copy(f"COPY catalog_eval.product ({columns}) FROM STDIN") as copy:
        for index in range(size):
            entry = items[index % len(items)]
            number = index // len(items)
            name = entry["name"] if number == 0 else f"{entry['name']} серия {number:02}"
            key = canonical_key(name)
            row = (index + 1, name, key)
            copy.write_row((*row, embedding(key)) if vector else row)
    if vector:
        conn.execute("SET maintenance_work_mem = '256MB'")
        conn.execute((ROOT / "002_vector.sql").read_text(encoding="utf-8"))
    conn.execute("ANALYZE catalog_eval.product")
    if vector:
        with conn.transaction():
            conn.execute("SET LOCAL enable_seqscan = off")
            plan = conn.execute("EXPLAIN " + VECTOR, {"v": embedding("ваниль молоко")}).fetchall()
        assert any("catalog_eval_hnsw" in line for (line,) in plan), plan
        (RESULTS / f"hnsw-plan-{size}.txt").write_text(
            "\n".join(line for (line,) in plan) + "\n", encoding="utf-8",
        )


def quality(conn, modes):
    details = []
    metrics = []
    queries = records("queries.csv")
    for mode in modes:
        conn.execute("SET enable_seqscan = " + ("off" if mode == "pgvector" else "on"))
        counts = defaultdict(Counter)
        added = defaultdict(list)
        for entry in queries:
            name, noise = entry["query"], entry["noise"]
            target = int(entry["target"]) if entry["target"] else None
            suggestions = suggest(conn, mode, name)
            ids = [row[0] for row in suggestions]
            matched = identity(conn, mode, name, suggestions)
            rank = ids.index(target) + 1 if target in ids else 0
            key = name.strip().lower() if mode == "baseline" else canonical_key(name)
            if matched is None and key and len(added[key]) == 1:
                matched = added[key][0][0]
            expected = target if target is not None else entry["novel"]
            stored_identity = next(
                (label for row_id, label in added.get(key, ()) if row_id == matched), matched,
            )
            duplicate = target is not None and matched is None
            false_merge = matched is not None and stored_identity != expected
            if matched is None:
                added[key].append((1001 + sum(len(values) for values in added.values()), expected))
            for group in (noise, "all"):
                c = counts[group]
                c["attempts"] += 1
                c["positive"] += target is not None
                c["novel"] += target is None
                c["hits"] += bool(rank)
                c["rr"] += 1 / rank if rank else 0
                c["created"] += matched is None
                c["duplicates"] += duplicate
                c["merges"] += matched is not None
                c["false_merges"] += false_merge
                c["false_novel"] += false_merge and target is None
            details.append((mode, noise, name, target, entry["distractor"], entry["novel"],
                            " ".join(map(str, ids)), rank, matched, int(duplicate), int(false_merge)))
        for group, c in counts.items():
            metrics.append({
                "mode": mode, "noise": group, **c,
                "recall5": c["hits"] / c["positive"] if c["positive"] else None,
                "precision5": c["hits"] / (5 * c["positive"]) if c["positive"] else None,
                "mrr5": c["rr"] / c["positive"] if c["positive"] else None,
                "dcr_final": c["duplicates"] / (1000 + c["created"]) if group == "all" else None,
                "dcr_created": c["duplicates"] / c["created"] if c["created"] else None,
                "duplicate_risk": c["duplicates"] / c["positive"] if c["positive"] else None,
                "fmr": c["false_merges"] / c["merges"] if c["merges"] else None,
                "novel_fmr": c["false_novel"] / c["novel"] if c["novel"] else None,
            })
    write_csv(RESULTS / "predictions.csv",
              ["mode", "noise", "query", "target", "distractor", "novel", "top5",
               "rank", "matched", "duplicate", "false_merge"], details)
    return metrics


def aggregation():
    rows = records("operations.csv")
    truth = defaultdict(Decimal)
    raw = defaultdict(Decimal)
    dimensions = defaultdict(set)
    for row in rows:
        key = (int(row["product"]), row["operation"], row["base"])
        truth[key] += Decimal(row["expected"])
        raw[key] += Decimal(row["quantity"])
        dimensions[key[:2]].add(row["base"])
    normalized = aggregate_quantities(
        (int(row["product"]), row["operation"], row["unit"], row["quantity"]) for row in rows
    )
    metrics = []
    for mode, totals in (("baseline", raw), ("hybrid", normalized), ("pgvector", normalized)):
        for unit in ("г", "мл", "шт", "comparable"):
            keys = [key for key in truth if key[2] == unit or (unit == "comparable" and key[2] != "шт")]
            metrics.append({
                "mode": mode, "unit": unit, "groups": len(keys),
                "mae": float(mean(abs(totals[key] - truth[key]) for key in keys)) if unit != "comparable" else None,
                "mape": float(mean(abs(totals[key] - truth[key]) / truth[key] for key in keys)),
                "mixed_output_groups": sum(len(units) > 1 for units in dimensions.values()) if mode == "baseline" else 0,
            })
    write_csv(RESULTS / "aggregation.csv", ["product", "operation", "unit", "truth", "raw", "normalized"],
              [(*key, value, raw[key], normalized[key]) for key, value in truth.items()])
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("size", type=int, choices=(1000, 10000, 100000))
    parser.add_argument("--no-vector", action="store_true")
    parser.add_argument("--quality", action="store_true")
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    with connect() as conn:
        prepare(conn, args.size, not args.no_vector)
        if args.quality:
            result = {
                "postgres": conn.info.server_version,
                "catalog_size": args.size,
                "ranking": quality(conn, MODES[:2] if args.no_vector else MODES),
                "aggregation": aggregation(),
            }
            (RESULTS / "quality.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")
