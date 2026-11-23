"""Build the metrics table from Playwright trial records and the PostgreSQL audit."""
import csv
import json
from collections import Counter, defaultdict
from math import ceil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PROFILES = ("stable", "slow", "intermittent", "offline")
MODES = ("online-only", "offline-first")


def percentiles(values):
    values = sorted(values)
    return {
        "n": len(values),
        **{f"p{q}": round(values[ceil(q * len(values) / 100) - 1], 2) if values else None
           for q in (50, 95)},
    }


def summarize(runs, audit):
    mutations = defaultdict(Counter)
    for event in audit["mutations"]:
        key = event["event"], event["item_id"] if event["event"] != "checkout" else None
        mutations[event["group_id"]][key] += 1
    keys = {(event["user_id"], event["operation_id"]) for event in audit["idempotency"]}
    groups = [row["group"] for row in runs]
    if len(groups) != len(set(groups)):
        raise ValueError("Идентификаторы групп повторяются. Используйте данные одного запуска.")

    metrics = []
    for profile in PROFILES:
        for mode in MODES:
            trials = [row for row in runs if (row["profile"], row["mode"]) == (profile, mode)]
            actions = [action for row in trials for action in row["actions"]]
            losses = duplicates = success = audit_anomalies = 0
            by_action = Counter()
            for row in trials:
                journal = mutations[row["group"]]
                for action in row["actions"]:
                    kind = action["kind"]
                    event = {"mark": "purchased", "edit": "quantity", "checkout": "checkout"}[kind]
                    count = journal[event, action.get("id")]
                    if kind != "mark":
                        duplicates += max(0, count - 1)
                        if kind == "checkout" and count <= 1 and any(
                            item["duplicate"] for item in row["actions"] if item["kind"] == "mark"
                        ):
                            duplicates += 1
                        losses += "acceptedAt" in action and not (action["applied"] and count >= 1)
                    successful = action["success"] and count == 1 and not action["duplicate"]
                    success += successful
                    by_action[kind] += successful
                audit_anomalies += sum(
                    bool(request["key"]) and (row["userId"], request["key"]) not in keys
                    for request in row["requests"] if request["status"] is not None
                    and 200 <= request["status"] < 300
                )
            metrics.append({
                "profile": profile, "mode": mode, "runs": len(trials),
                "list_opened": sum("acceptedAt" in row["opening"] for row in trials),
                "planned": len(actions), "success": success, "success_by_action": dict(by_action),
                "success_pct": round(100 * success / len(actions), 4) if actions else None,
                "lost": losses, "duplicates": duplicates, "conflicts": sum(
                    request["status"] in (409, 422) for row in trials for request in row["requests"]
                ),
                "audit_anomalies": audit_anomalies,
                "accepted_ui": percentiles(action["uiMs"] for action in actions if "uiMs" in action),
                "writes_ui": percentiles(action["uiMs"] for action in actions
                                         if action["kind"] != "mark" and "uiMs" in action),
                "open_ui": percentiles(row["opening"]["uiMs"] for row in trials if "uiMs" in row["opening"]),
                "reconnect_sync": percentiles(row["syncMs"] for row in trials if row["syncMs"] is not None),
                "online_delivery": percentiles(ms for row in trials for ms in row["deliveryMs"])
                if profile in ("stable", "slow") else None,
                "runs_pending": sum(row["losses"] > 0 for row in trials),
            })
    for baseline, experiment in zip(metrics[::2], metrics[1::2]):
        base = baseline["success_pct"]
        current = experiment["success_pct"]
        experiment["gain_pp"] = round(current - base, 4) if base is not None and current is not None else None
    return metrics


def main():
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in (ROOT / "trials").glob("*.json")]
    audit = json.loads((ROOT / "db-audit.json").read_text(encoding="utf-8"))
    metrics = summarize(runs, audit)
    if "--allow-incomplete" not in sys.argv and any(row["runs"] != 50 for row in metrics):
        raise ValueError("Ожидалось по 50 прогонов на профиль и вариант.")
    (ROOT / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    columns = ("profile", "mode", "runs", "list_opened", "planned", "success", "success_pct", "gain_pp",
               "lost", "duplicates", "conflicts", "runs_pending", "audit_anomalies")
    timings = ("accepted_ui", "writes_ui", "open_ui", "reconnect_sync", "online_delivery")
    with (ROOT / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow([*columns, *(f"{key}_{q}" for key in timings for q in ("p50", "p95", "n"))])
        for row in metrics:
            writer.writerow([*(row.get(key) for key in columns),
                             *((row.get(key) or {}).get(q) for key in timings for q in ("p50", "p95", "n"))])


if __name__ == "__main__":
    main()


