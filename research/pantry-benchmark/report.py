"""Summarize the completed benchmark, including the predeclared thresholds."""
import csv
from decimal import Decimal
import json
import math
from pathlib import Path
import re
from statistics import median

OUT = Path(__file__).resolve().parent / "results"
READS = ("pantry", "usage")
WRITES = ("consumption", "waste")
OPERATIONS = READS + WRITES


def load_csv(name):
    with (OUT / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def percentiles(requests, size, profile, mode, operation, repeat):
    values = sorted(float(row["ms"]) for row in requests if
                    (row["size"], row["profile"], row["mode"], row["kind"], row["repeat"])
                    == (size, profile, mode, operation, repeat) and 200 <= int(row["status"]) < 300)
    return values[math.ceil(len(values) * .95) - 1] if values else None


def main():
    metrics = load_csv("metrics.csv")
    resources = load_csv("resources.csv")
    requests = load_csv("requests.csv")
    primary = {(str(row["size"]), row["mode"]): row
               for row in json.loads((OUT / "integrity.json").read_text(encoding="utf-8"))}
    extra = {(str(row["size"]), row["mode"]): row
             for row in json.loads((OUT / "transaction-audit.json").read_text(encoding="utf-8"))}
    metrics_by_key = {(r["size"], r["profile"], r["mode"], r["kind"]): r for r in metrics}

    def resource(size, profile, mode, column):
        return median(float(r[column]) for r in resources
                      if (r["size"], r["profile"], r["mode"]) == (size, profile, mode))

    def correctness(size, mode):
        p, e = primary[size, mode], extra[size, mode]
        return (all(p["initial_equivalence"].values())
                and all(p["after_race_usage_equivalence"].values())
                and p["seeded_count_after_load"] == int(size)
                and p["lost"] == p["unexpected_or_duplicate"] == e["open_lot_mismatches"] == 0
                and e["seed_matches_baseline"] and Decimal(e["race_remaining"]) == 0
                and p["race_events"] == 1 and p["race_http_statuses"] == [201, 422, 422, 422]
                and (mode != "C" or (
                    p["hourly_usage_mismatches"] == p["lot_balance_mismatches"] == 0
                    and e["quantity_adjustment_updates_visible_remaining"]
                    and e["event_and_projection_change_before_rollback"]
                    and e["event_and_projections_restored_by_rollback"]
                    and all(e["history_mutation_rejected"].values()))))

    criteria = []
    sizes = sorted({r["size"] for r in metrics}, key=int)
    for size in sizes:
        for profile in ("90-10", "70-30"):
            for mode in ("B", "C"):
                p95 = {operation: float(metrics_by_key[size, profile, mode, operation]["p95_reduction_pct"])
                       for operation in OPERATIONS}
                reproducible = {}
                for op in READS:
                    repeats = sorted({r["repeat"] for r in requests})
                    pairs = [(percentiles(requests, size, profile, m, op, repeat)
                              for m in ("A", mode)) for repeat in repeats]
                    reproducible[op] = all(a is not None and b is not None and b < a for a, b in pairs)
                cpu, mem = {m: resource(size, profile, m, "api_cpu_s") for m in ("A", mode)}, {
                    m: resource(size, profile, m, "api_peak_rss_mib") for m in ("A", mode)}
                row = {"size": int(size), "profile": profile, "mode": mode,
                       "p95_reduction_pct": p95,
                       "read_p95_meets_20_percent": all(p95[k] >= 20 for k in READS),
                       "write_p95_growth_at_most_10_percent": all(p95[k] >= -10 for k in WRITES),
                       "reproducible_improvement": reproducible,
                       "baseline_cpu_s_median": cpu["A"], "candidate_cpu_s_median": cpu[mode],
                       "baseline_peak_rss_mib_median": mem["A"], "candidate_peak_rss_mib_median": mem[mode],
                       "cpu_and_ram_reduced": cpu[mode] < cpu["A"] and mem[mode] < mem["A"],
                       "integrity_pass": correctness(size, mode),
                       "no_load_errors": all(int(metrics_by_key[size, profile, m, op]["errors"]) == 0
                                             for op in OPERATIONS for m in ("A", mode))}
                criteria.append(row)
    required = [row for row in criteria if row["mode"] == "C" and row["size"] >= 100000]
    full = all(row["read_p95_meets_20_percent"] and row["write_p95_growth_at_most_10_percent"]
               and row["cpu_and_ram_reduced"] and row["integrity_pass"] and row["no_load_errors"]
               and all(row["reproducible_improvement"].values()) for row in required)
    integrity_pass = all(row["integrity_pass"] for row in criteria if row["mode"] == "C")
    partial = integrity_pass and any(any(row["reproducible_improvement"].values())
                                    for row in criteria if row["mode"] == "C")
    verdict = "подтверждена" if full and integrity_pass else (
        "частично подтверждена" if partial else "не подтверждена")
    thresholds = []
    for profile in ("90-10", "70-30"):
        for mode in ("B", "C"):
            for op in READS:
                eligible = [row["size"] for row in criteria if row["mode"] == mode
                            and row["profile"] == profile and row["reproducible_improvement"][op]]
                thresholds.append({"mode": mode, "profile": profile, "operation": op,
                                   "first_tested_size_with_repeatable_p95_gain": min(eligible, default=None)})
    (OUT / "criteria.json").write_text(json.dumps(
        {"verdict": verdict, "criteria": criteria, "thresholds": thresholds},
        indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        f"Гипотеза {verdict.upper()}.",
        "",
        "Эффект p95 относительно A, %. Положительное значение означает сокращение задержки.",
        "Записи | Чтение/запись | Схема | Кладовая | Статистика | Потребление | Списание | CPU A→вариант, с | RAM A→вариант, МиБ",
    ]
    for r in criteria:
        p = r["p95_reduction_pct"]
        lines.append(f'{r["size"]:>6} | {r["profile"]:>6} | {r["mode"]} | '
                     + " | ".join(f"{p[k]:>7.2f}" for k in OPERATIONS)
                     + f' | {r["baseline_cpu_s_median"]:.3f}→{r["candidate_cpu_s_median"]:.3f}'
                     + f' | {r["baseline_peak_rss_mib_median"]:.2f}→{r["candidate_peak_rss_mib_median"]:.2f}')
    lines += ["", "Минимальный протестированный объём с улучшением p95 в каждом повторе:"]
    for r in thresholds:
        lines.append(f'{r["mode"]}, {r["profile"]}, {r["operation"]} — '
                     f'{r["first_tested_size_with_repeatable_p95_gain"] or "не найден"}')
    lines += ["", "Целостность по вариантам (успешные запросы сверх доступного остатка видны по числу событий):"]
    for size in sizes:
        for mode in ("A", "B", "C"):
            p, e = primary[size, mode], extra[size, mode]
            lines.append(f'{size}, {mode}: гонка {p["race_http_statuses"]}, событий {p["race_events"]}, '
                         f'финальный остаток {e["race_remaining"]}; потерь при нагрузке {p["lost"]}, '
                         f'лишних событий {p["unexpected_or_duplicate"]}, '
                         f'расхождений строк кладовой {e["open_lot_mismatches"]}.')
    lines += ["", "Проверка критериев для гибридной схемы на 100 000 и 500 000 записей:"]
    for row in required:
        flags = [label for key, label in (
            ("read_p95_meets_20_percent", "чтение ≥20%"),
            ("write_p95_growth_at_most_10_percent", "рост p95 записи ≤10%"),
            ("cpu_and_ram_reduced", "снижение CPU и RAM"),
            ("integrity_pass", "целостность"),
            ("no_load_errors", "отсутствие ошибок при нагрузке")
        ) if not row[key]]
        if not all(row["reproducible_improvement"].values()):
            flags.append("снижение p95 чтения в обоих повторах")
        description = "все критерии выполнены" if not flags else "не выполнены: " + ", ".join(flags)
        lines.append(f'{row["size"]}, {row["profile"]} — {description}.')
    lines += ["", "Одиночные планы на максимальном объёме. Это SQL-время вне HTTP-нагрузки.",
              "Схема | SQL кладовой, мс | SQL годовой статистики, мс | Медиана Δ WAL LSN на INSERT потребления / списания, байт"]
    for mode in ("A", "B", "C"):
        plan = (OUT / "plans" / f"{sizes[-1]}-{mode}.txt").read_text(encoding="utf-8")
        times = [float(value) for value in re.findall(r"Execution Time: ([0-9.]+) ms", plan)]
        stats_time = sum(times[1:3]) if mode == "A" else times[2]
        wal_bytes = extra[sizes[-1], mode]["wal_lsn_delta_bytes_per_insert_median"].values()
        lines.append(f"{mode} | {times[0]:.3f} | {stats_time:.3f} | " + " / ".join(map(str, wal_bytes)))
    lines += ["", "Сравнение B и C на максимальном объёме, p95 HTTP в мс:"]
    for profile in ("90-10", "70-30"):
        for operation in READS:
            b = metrics_by_key[sizes[-1], profile, "B", operation]["p95_ms"]
            c = metrics_by_key[sizes[-1], profile, "C", operation]["p95_ms"]
            lines.append(f"{profile}, {operation}: B {b}, C {c}.")
    lines += ["", "Детали воспроизведения и ограничения — в README.txt."]
    (OUT / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(verdict)


if __name__ == "__main__":
    main()
