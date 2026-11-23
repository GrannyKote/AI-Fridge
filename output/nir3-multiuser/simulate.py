import copy
import csv
import gzip
import json
import math
import random
import statistics
from pathlib import Path

OUT = Path(__file__).resolve().parent
SEED = 481722
HORIZON = 1200
MODES = ("A", "B", "C")

# Each scenario has at most one active line per product.
SCENARIOS = [
    ("Добавление и покупка", {}, {}, [("list", "milk", 1), ("buy", "milk", 1)], "milk"),
    ("Покупка части списка", {}, {"bread": 1, "apple": 1}, [("buy", "bread", 1)], "bread"),
    ("Покупка разных товаров", {}, {"rice": 1, "yogurt": 1}, [("buy", "rice", 1), ("buy", "yogurt", 1)], "yogurt"),
    ("Покупка и добавление позиции", {}, {"eggs": 1}, [("list", "cheese", 1), ("buy", "eggs", 1)], "eggs"),
    ("Расход и пополнение", {"milk": 2}, {"milk": 1}, [("use", "milk", 1), ("buy", "milk", 1)], "milk"),
    ("Повторное оформление позиции", {}, {"coffee": 1}, [("buy", "coffee", 1), ("buy", "coffee", 1)], "coffee"),
]

def commit(old, action):
    kind, product, amount = action
    state = copy.deepcopy(old)
    if kind == "buy":
        if product not in state["shopping"]:
            return old, None
        del state["shopping"][product]
        state["pantry"][product] = state["pantry"].get(product, 0) + amount
    elif kind == "use":
        assert state["pantry"][product] >= amount
        state["pantry"][product] -= amount
    else:
        state["shopping"][product] = amount
    state["version"] += 1
    patch = {"base": old["version"], "version": state["version"], "set": {}, "remove": {}}
    for key in ("pantry", "shopping"):
        patch["set"][key] = {k:v for k,v in state[key].items() if old[key].get(k) != v}
        patch["remove"][key] = sorted(old[key].keys() - state[key].keys())
    return state, patch

def apply(old, patch):
    assert old["version"] == patch["base"]
    state = copy.deepcopy(old)
    for key in ("pantry", "shopping"):
        for item in patch["remove"][key]:
            del state[key][item]
        state[key].update(patch["set"][key])
    state["version"] = patch["version"]
    return state

def size(value):
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return 240 + len(gzip.compress(payload, mtime=0))

def trace(rng):
    windows = []
    start = rng.uniform(15, 110)
    while start < HORIZON:
        end = min(start + rng.uniform(85, 470), HORIZON)
        windows.append((start, end, rng.choice((8, 16, 32, 64, 128)) / 8))
        start = end + rng.uniform(45, 275)
    return windows

def deliver(windows, jobs):
    # Equal bandwidth sharing among ready responses. Bytes survive a disconnect.
    remaining = {key: float(count) for key, (_, count) in jobs.items()}
    ready = {key: time for key, (time, _) in jobs.items()}
    complete = {}
    for start, end, speed in windows:
        now = start
        while remaining and now < end - 1e-9:
            active = [key for key in remaining if ready[key] <= now + 1e-9]
            upcoming = min((ready[key] for key in remaining if ready[key] > now + 1e-9), default=math.inf)
            if not active:
                now = min(upcoming, end)
                continue
            share = speed / len(active)
            duration = min(end, upcoming, now + min(remaining[k] for k in active) / share) - now
            now += duration
            for key in active:
                remaining[key] -= duration * share
                if remaining[key] <= 1e-8:
                    complete[key] = now
                    del remaining[key]
    return complete

def fixtures(rng, scenario):
    _, pantry, shopping, actions, focal = scenario
    filler = rng.choice((12, 48, 192))
    base = {"pantry": dict(pantry), "shopping": dict(shopping), "version": 0}
    base["pantry"].update({f"product-{i:03d}-{rng.getrandbits(32):08x}": rng.randint(1, 8) for i in range(filler)})
    target = base
    patches = []
    rejections = 0
    for action in actions:
        target, patch = commit(target, action)
        if patch is None:
            rejections += 1
        else:
            patches.append(patch)
    verified = base
    for patch in patches:
        verified = apply(verified, patch)
    assert verified == target
    assert focal in target["pantry"] and focal not in target["shopping"]
    return base, target, patches, focal, filler, rejections

def run(rng, scenario_id, trial):
    scenario = SCENARIOS[scenario_id - 1]
    base, target, patches, focal, filler, rejections = fixtures(rng, scenario)
    # The observer's cache is taken after the initial list already shows the
    # focal entry. Earlier preparatory actions remain in the server history.
    if scenario_id == 1:
        base = apply(base, patches[0])
        patches = patches[1:]
    assert focal in base["shopping"]
    windows = trace(rng)
    ready_list = rng.uniform(35, 330)
    ready_pantry = rng.uniform(35, 330)
    # B and C get the same server-ready timestamp. C streams its ordered
    # records in one response, with a separately applicable record per commit.
    a_sizes = {key: size({"version": target["version"], key: target[key]}) for key in ("shopping", "pantry")}
    b_size = size(target)
    c_sizes = [size(patch) - 240 + (240 if i == 0 else 0) for i, patch in enumerate(patches)]
    a = deliver(windows, {"shopping": (ready_list, a_sizes["shopping"]), "pantry": (ready_pantry, a_sizes["pantry"])})
    b = deliver(windows, {"snapshot": (ready_list, b_size)})
    # The completion time of a prefix on a single stream gives the publication
    # time of its final transaction. All focal purchases are the final commit.
    c_times = [deliver(windows, {"prefix": (ready_list, sum(c_sizes[:i]))}).get("prefix") for i in range(1, len(c_sizes)+1)]
    first_end = windows[0][1]
    records = []
    for mode in MODES:
        local = copy.deepcopy(base)
        if mode == "A":
            decision_at = a.get("shopping")
            full_at = max(a.values()) if len(a) == 2 else None
            for key in a:
                local[key] = target[key]
        elif mode == "B":
            decision_at = full_at = b.get("snapshot")
            if full_at is not None:
                local = target
        else:
            decision_at = full_at = c_times[-1]
            for patch, arrival in zip(patches, c_times):
                if arrival is not None:
                    local = apply(local, patch)
        error = int(focal in local["shopping"])
        assert error == int(decision_at is None)
        exact = int(all(local[k] == target[k] for k in ("shopping", "pantry")))
        assert full_at is None or exact
        mixed = int(mode == "A" and len(a) == 1)
        offered = {"A": sum(a_sizes.values()), "B": b_size, "C": sum(c_sizes)}[mode]
        records.append(dict(scenario=scenario_id, trial=trial, mode=mode, pantry_filler=filler,
                            horizon_ms=HORIZON, first_window_end_ms=first_end, ready_list_ms=ready_list,
                            ready_pantry_ms=ready_pantry, trace=json.dumps(windows, separators=(",", ":")),
                            error=error, mixed=mixed, decision_ms=decision_at, capped_ms=decision_at if decision_at is not None else HORIZON,
                            first_window=int(decision_at is not None and decision_at <= first_end),
                            full_state=int(full_at is not None), exact_content=exact, full_state_ms=full_at, offered_bytes=offered,
                            server_rejections=rejections, focal=focal, expected_focal_stock=target["pantry"][focal],
                            observed_focal_stock=local["pantry"].get(focal, 0)))
    return records

def summarize(rows):
    result = {}
    for mode in MODES:
        group = [r for r in rows if r["mode"] == mode]
        result[mode] = {"n": len(group)}
        for metric in ("error", "mixed", "first_window", "full_state", "exact_content"):
            result[mode][metric] = sum(r[metric] for r in group)
        for metric in ("capped_ms", "offered_bytes"):
            result[mode][metric] = statistics.mean(r[metric] for r in group)
    result["error_A_minus_C_pp"] = 100 * (result["A"]["error"] - result["C"]["error"]) / result["A"]["n"]
    result["time_B_minus_C_ms"] = result["B"]["capped_ms"] - result["C"]["capped_ms"]
    return result

def main():
    assert deliver([(0, 10, 1), (20, 30, 1)], {"x": (0, 15)}) == {"x": 25}
    assert deliver([(0, 20, 1)], {"x": (0, 4), "y": (0, 10)}) == {"x": 8, "y": 14}
    rng = random.Random(SEED)
    rows = [row for scenario in range(1, 7) for trial in range(1, 51) for row in run(rng, scenario, trial)]
    assert len(rows) == 900
    assert all(r["server_rejections"] == (r["scenario"] == 6) for r in rows)
    with (OUT / "trials.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    result = {"seed": SEED, "horizon_ms": HORIZON, "overall": summarize(rows), "scenarios": {
        str(i): {"name": SCENARIOS[i-1][0], **summarize([r for r in rows if r["scenario"] == i])}
        for i in range(1, 7)}}
    (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["overall"], indent=2))

if __name__ == "__main__":
    main()

