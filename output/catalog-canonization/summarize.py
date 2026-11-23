"""Summarize the measured quality, false merges and raw Locust requests."""
from collections import Counter, defaultdict
import csv
import json
from math import ceil

from dataset import ROOT, DATA, write_csv

RESULTS = ROOT / 'results'
from search import MODES

LABELS = {
    "all": "Все запросы с продуктом",
    "case_punctuation": "Регистр и пунктуация",
    "typo": "Опечатки",
    "word_order": "Порядок слов",
    "morphology": "Морфология",
    "known_brand_pack": "Известный бренд и фасовка",
    "unknown_brand_pack": "Неизвестный бренд и фасовка",
    "abbreviation": "Сокращения",
    "hidden_synonym": "Скрытые синонимы",
    "trap_novel": "Ловушки: новый продукт",
    "trap_present": "Ловушки: продукт в каталоге",
}


def read(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def percentile(values, p):
    ordered = sorted(values)
    return ordered[ceil(p * len(ordered)) - 1]


def export_load():
    aggregates = defaultdict(lambda: ([], []))
    rows = []
    for size in (1000, 10000, 100000):
        for mode in MODES:
            for trial in (1, 2, 3):
                path = RESULTS / f"latency-{size}-{mode}-{trial}.csv"
                samples = read(path)
                assert all(row["failed"] == "False" and row["server_ms"] for row in samples), path
                http = [float(row["http_ms"]) for row in samples]
                server = [float(row["server_ms"]) for row in samples]
                assert len(http) >= 200, path
                for target, source in zip(aggregates[size, mode], (http, server)):
                    target.extend(source)
                rows.append((size, mode, trial, len(http), 0, percentile(http, .5),
                             percentile(http, .95), percentile(server, .5), percentile(server, .95)))
    for (size, mode), (http, server) in aggregates.items():
        rows.append((size, mode, "pooled", len(http), 0, percentile(http, .5),
                     percentile(http, .95), percentile(server, .5), percentile(server, .95)))
    write_csv(RESULTS / "latency.csv",
              ["catalog", "mode", "trial", "requests", "failures", "http_p50_ms", "http_p95_ms",
               "server_p50_ms", "server_p95_ms"], rows)
    return rows


def export_quality(quality):
    ranking = quality["ranking"]
    fields = list(dict.fromkeys(key for record in ranking for key in record))
    write_csv(RESULTS / "ranking.csv", fields, ([row.get(key) for key in fields] for row in ranking))
    predictions = read(RESULTS / "predictions.csv")
    names = {row["id"]: row["name"] for row in read(DATA / "catalog.csv")}
    audit = []
    for row in predictions:
        if row["distractor"] or row["false_merge"] == "1":
            top = row["top5"].split()
            audit.append((row["mode"], row["noise"], row["query"], names.get(row["target"], row["novel"]),
                          names.get(row["distractor"]), top[0] if top else "",
                          names.get(top[0]) if top else "", row["matched"], names.get(row["matched"]),
                          int(row["false_merge"]), row["distractor"] in top))
    write_csv(RESULTS / "merge-audit.csv",
              ["mode", "noise", "query", "expected", "distractor", "top1_id", "top1",
               "matched_id", "matched", "false_merge", "distractor_in_top5"], audit)
    return predictions, audit


def draw_map(ranking):
    import matplotlib.pyplot as plt

    scores = {(row["noise"], row["mode"]): row["recall5"] for row in ranking}
    classes = [key for key in LABELS if key != "trap_novel"]
    values = [[100 * scores[group, mode] for mode in MODES] for group in classes]
    fig, ax = plt.subplots(figsize=(8.3, 5.1), layout="constrained")
    colored = ax.imshow(values, aspect="auto", vmin=0, vmax=100, cmap="Blues")
    ax.set_title("Полнота автодополнения по классам шума")
    ax.set_xticks(range(len(MODES)), ("Baseline", "Гибрид", "pgvector"))
    ax.set_yticks(range(len(classes)), [LABELS[group] for group in classes])
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            ax.text(j, i, f"{value:.1f}%", ha="center", va="center",
                    color="white" if value >= 60 else "#102c55")
    fig.colorbar(colored, ax=ax, label="Recall@5, %", shrink=.83)
    fig.savefig(RESULTS / "recall-heatmap.png", dpi=175)
    plt.close(fig)


def replay_quality():
    catalog = read(DATA / "catalog.csv")
    labels = {row["query"]: row for row in read(DATA / "queries.csv")}
    ids = {int(row["id"]) for row in catalog}
    seen = set()
    counts = defaultdict(Counter)
    for row in read(RESULTS / "predictions.csv"):
        mode, query = row["mode"], row["query"]
        label = labels[query]
        assert mode in MODES and (mode, query) not in seen
        seen.add((mode, query))
        assert all(row[key] == label[key] for key in ("noise", "target", "distractor", "novel"))
        top = [int(item) for item in row["top5"].split()]
        assert len(top) == len(set(top)) <= 5 and set(top) <= ids
        target = int(label["target"]) if label["target"] else None
        rank = top.index(target) + 1 if target in top else 0
        assert rank == int(row["rank"])
        merged = bool(row["matched"])
        duplicate = target is not None and not merged
        assert duplicate == bool(int(row["duplicate"]))
        false_merge = merged and (target is None or int(row["matched"]) != target)
        assert false_merge == bool(int(row["false_merge"]))
        for group in ("all", label["noise"]):
            c = counts[mode, group]
            c["attempts"] += 1
            c["positive"] += target is not None
            c["novel"] += target is None
            c["hits"] += bool(rank)
            c["rr"] += 1 / rank if rank else 0
            c["created"] += not merged
            c["duplicates"] += duplicate
            c["merges"] += merged
            c["false_merges"] += false_merge
            c["false_novel"] += false_merge and target is None
    assert len(seen) == len(MODES) * len(labels)
    ranking = []
    for (mode, group), c in counts.items():
        ranking.append({
            "mode": mode, "noise": group, **c,
            "recall5": c["hits"] / c["positive"] if c["positive"] else None,
            "precision5": c["hits"] / (5 * c["positive"]) if c["positive"] else None,
            "mrr5": c["rr"] / c["positive"] if c["positive"] else None,
            "dcr_final": c["duplicates"] / (len(catalog) + c["created"]) if group == "all" else None,
            "dcr_created": c["duplicates"] / c["created"] if c["created"] else None,
            "duplicate_risk": c["duplicates"] / c["positive"] if c["positive"] else None,
            "fmr": c["false_merges"] / c["merges"] if c["merges"] else None,
            "novel_fmr": c["false_novel"] / c["novel"] if c["novel"] else None,
        })
    return {"catalog_size": len(catalog), "ranking": ranking}


def main():
    quality = replay_quality()
    (RESULTS / "quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    rows, audit = export_quality(quality)
    draw_map(quality["ranking"])
    latency = export_load()
    baseline, hybrid = (next(row for row in quality["ranking"]
                            if row["mode"] == mode and row["noise"] == "all") for mode in MODES[:2])
    pair = {mode: {row["query"]: int(row["duplicate"]) for row in rows if row["mode"] == mode}
            for mode in MODES[:2]}
    improved = sum(value > pair["hybrid"][key] for key, value in pair["baseline"].items())
    worsened = sum(value < pair["hybrid"][key] for key, value in pair["baseline"].items())
    reduction = 1 - hybrid["dcr_final"] / baseline["dcr_final"]
    recall_gain = hybrid["recall5"] - baseline["recall5"]
    max_http95 = max(row[6] for row in latency if row[1] == "hybrid" and row[2] != "pooled")
    max_server95 = max(row[8] for row in latency if row[1] == "hybrid" and row[2] != "pooled")
    criteria = {
        "dcr_reduction_at_least_50_pct": reduction >= .5,
        "recall_at_least_85_pct": hybrid["recall5"] >= .85,
        "recall_gain_at_least_30_points": recall_gain >= .30,
        "fmr_at_most_2_pct": hybrid["fmr"] <= .02,
        "http_p95_at_most_50_ms_in_every_trial": max_http95 <= 50,
    }
    summary = {
        "criteria": criteria, "dcr_relative_reduction": reduction, "recall_gain": recall_gain,
        "max_hybrid_http_p95_ms": max_http95, "max_hybrid_server_p95_ms": max_server95,
        "duplicate_outcomes_improved": improved, "duplicate_outcomes_worsened": worsened,
        "false_merges_in_audit_by_mode": {
            mode: sum(row[0] == mode and row[-2] for row in audit) for mode in MODES
        },
        "verdict": ("confirmed" if all(criteria.values()) else "partially_confirmed"
                    if reduction > 0 and hybrid["fmr"] <= .02 else "not_confirmed"),
    }
    (RESULTS / "criteria.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
