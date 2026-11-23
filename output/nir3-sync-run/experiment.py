"""AI-Fridge paired shelf-decision benchmark. Python 3.10+, standard library.

Run: python research/nir3-sync/experiment.py
The fixtures and network timelines are synthetic. gzip sizes are measured; time is modeled.
Preselected thresholds: 1 percentage point (A minus C); 20.48 ms (B minus C).
"""
import csv
import gzip
import json
import math
import random
import statistics
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

OUT = Path(__file__).resolve().parent
SEED = 481721
RUNS = 3600
HEADER = 240  # fixed response overhead, bytes; identical for each message


def product(i):
    names = ('Молоко', 'Кефир', 'Яблоки', 'Сыр', 'Рис', 'Йогурт', 'Морковь', 'Яйца')
    return dict(id=i, product_id=i, name=names[i % 8] + ' ' + str(i), quantity=1,
                remaining=1, price=50 + i % 199, unit='шт', unit_id=1, category_id=2,
                category='Продукты', storage_place_id=1, storage_place='Холодильник',
                best_before=f'2026-12-{1+i%28:02d}', first_reminder_days=4,
                second_reminder_days=1, first_reminder_shown=None, first_reminder_seen=None,
                second_reminder_shown=None, second_reminder_seen=None, is_consumed=False,
                is_wasted=False, is_deleted=False, is_over=False)


def states(n, m):
    existing = [product(i) for i in range(1, n + 1)]
    added = [product(i) for i in range(n + 1, n + m + 1)]
    old_list = [dict(id=1000+j, name=row['name'], quantity=1, unit='шт',
                     category_id=2, category='Продукты', expires_in=7)
                for j, row in enumerate(added)]
    old = dict(rev=0, pantry=existing, shopping=old_list)
    latest = dict(rev=1, pantry=existing + added, shopping=[])
    patch = dict(base=0, rev=1, add=added, remove=[x['id'] for x in old_list])
    return old, latest, patch


def apply_patch(state, patch):
    if state['rev'] == patch['rev']:
        return state
    if state['rev'] != patch['base']:
        raise ValueError('Snapshot required')
    removed = set(patch['remove'])
    return dict(rev=patch['rev'], pantry=state['pantry'] + patch['add'],
                shopping=[row for row in state['shopping'] if row['id'] not in removed])


def wire_bytes(obj, codec):
    body = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode()
    if codec == 'gzip':
        body = gzip.compress(body, compresslevel=6, mtime=0)
    return HEADER + len(body)


@lru_cache(maxsize=None)
def sizes(n, m, codec):
    old, latest, patch = states(n, m)
    assert apply_patch(old, patch) == latest
    assert apply_patch(latest, patch) == latest
    return tuple(wire_bytes(x, codec) for x in
                 (latest['shopping'], latest['pantry'], latest, patch))


def arrivals(requests, rate):
    """Complete responses on a single link with equal sharing among ready streams."""
    pending = sorted(requests)
    active = {}
    finish = {}
    t = 0.
    while pending or active:
        if not active:
            t = pending[0][0]
        while pending and pending[0][0] <= t + 1e-8:
            _, name, size = pending.pop(0)
            active[name] = size
        next_start = pending[0][0] if pending else math.inf
        share = rate / len(active)
        end = min(next_start, t + min(active.values()) / share)
        for name in list(active):
            active[name] -= (end - t) * share
            if active[name] < 1e-7:
                finish[name] = end
                del active[name]
        t = end
    return finish


def simulate(n, m, kbps, w, shopping_start, pantry_start, codec):
    shopping, pantry, full, delta = sizes(n, m, codec)
    rate = kbps / 8  # decimal kbit/s -> bytes per millisecond
    a = arrivals([(shopping_start, 'list', shopping), (pantry_start, 'pantry', pantry)], rate)
    times = (a['list'], shopping_start + full/rate, shopping_start + delta/rate)
    mixed = (a['list'] <= w) != (a['pantry'] <= w)
    return times, mixed, a['pantry'], (shopping + pantry, full, delta)


def estimate(xs):
    mean = statistics.mean(xs)
    se = statistics.stdev(xs) / math.sqrt(len(xs))
    return [round(v, 5) for v in (mean, mean - 1.96*se, mean + 1.96*se)]


def summarize(rows):
    result = {}
    for name in 'ABC':
        result[name] = dict(errors=sum(r['err_'+name] for r in rows),
                            capped_ms=round(statistics.mean(r['wait_'+name] for r in rows), 3),
                            offered_bytes=round(statistics.mean(r['size_'+name] for r in rows), 2))
    result['A_minus_C_pp'] = estimate([(r['err_A'] - r['err_C'])*100 for r in rows])
    result['B_minus_C_ms'] = estimate([r['wait_B'] - r['wait_C'] for r in rows])
    result['mixed_A'] = sum(r['mixed_A'] for r in rows)
    result['mixed_A_wrong'] = sum(r['mixed_A'] and r['err_A'] for r in rows)
    result['both_views_rule_A_errors'] = sum(r['err_A_both'] for r in rows)
    result['pairs_A_correct_C_wrong'] = sum(not r['err_A'] and r['err_C'] for r in rows)
    result['pairs_C_correct_A_wrong'] = sum(r['err_A'] and not r['err_C'] for r in rows)
    result['n'] = len(rows)
    return result


@lru_cache(maxsize=None)
def reopened_list_sizes(n, m, count):
    _, checked_out, patch = states(n, m)
    latest = dict(checked_out)
    latest['shopping'] = [dict(id=8000+j, name=f'Новая позиция {j}', quantity=1,
                               unit='шт', category_id=2, category='Продукты', expires_in=7)
                          for j in range(count)]
    latest['rev'] += count
    assert all(item['name'] != patch['add'][0]['name'] for item in latest['shopping'])
    return tuple(wire_bytes(x, 'gzip') for x in
                 (latest['shopping'], latest['pantry'], latest, patch))


def explore_new_list(rows):
    """Post-hoc variation: a new list already exists before reconnection.
    C streams a chronological transaction log. Only time to the focal item's
    final correct decision is scored, not time to deliver the entire new list.
    """
    report = {}
    for count in (8, 32):
        errors = dict.fromkeys('ABC', 0)
        differences = []
        for row in rows:
            lst, pantry, snapshot, first_tx = reopened_list_sizes(
                row['rows'], row['checkout'], count)
            s, p, w = row['list_ready_ms'], row['pantry_ready_ms'], row['window_ms']
            rate = row['kbps']/8
            separate = arrivals([(s, 'list', lst), (p, 'pantry', pantry)], rate)
            times = (separate['list'], s+snapshot/rate, s+first_tx/rate)
            for name, finish in zip('ABC', times):
                errors[name] += int(finish > w)
            differences.append(100*(int(times[0] > w)-int(times[2] > w)))
        report[str(count)] = dict(errors=errors, A_minus_C_pp=estimate(differences))
    return report


def main():
    assert arrivals([(0, 'a', 100), (0, 'b', 300)], 10) == {'a': 20, 'b': 40}
    assert arrivals([(0, 'a', 100), (20, 'b', 300)], 10) == {'a': 10, 'b': 50}
    old, new, patch = states(12, 1)
    try:
        apply_patch(dict(old, rev=8), patch)
    except ValueError:
        pass
    else:
        raise AssertionError('Wrong base accepted')
    # Truncated response must never produce a partial local transaction.
    encoded = json.dumps(patch).encode()
    for length in range(len(encoded)):
        try:
            json.loads(encoded[:length])
        except (ValueError, UnicodeError):
            continue
        raise AssertionError('Truncated object accepted')
    rng = random.Random(SEED)
    groups = defaultdict(list)
    records = []
    for i in range(RUNS):
        n, m = rng.choice((12, 48, 192)), rng.choice((1, 3, 8))
        rate, w = rng.choice((100, 400)), rng.uniform(300, 1200)
        s, p = rng.uniform(400, 560), rng.uniform(400, 560)
        for codec in ('gzip', 'identity'):
            times, mixed, pantry_t, sizes_ = simulate(n, m, rate, w, s, p, codec)
            row = dict(trial=i, rows=n, checkout=m, kbps=rate, window_ms=w,
                       list_ready_ms=s, pantry_ready_ms=p, codec=codec,
                       mixed_A=int(mixed), err_A_both=int(min(pantry_t, times[0]) > w))
            for label, t, size in zip('ABC', times, sizes_):
                row['err_'+label] = int(t > w)
                row['wait_'+label] = min(w, t)
                row['finish_'+label] = t
                row['size_'+label] = size
            groups[codec].append(row)
            records.append(row)
    with (OUT/'trials.csv').open('w', newline='', encoding='utf-8') as f:
        out = csv.DictWriter(f, fieldnames=records[0].keys())
        out.writeheader()
        out.writerows(records)
    primary = groups['gzip']
    result = {name: summarize(rows) for name, rows in groups.items()}
    result['by_pantry_size'] = {str(n): summarize([r for r in primary if r['rows']==n])
                                for n in (12, 48, 192)}
    result['by_checkout_size'] = {str(m): summarize([r for r in primary if r['checkout']==m])
                                  for m in (1, 3, 8)}
    result['exploratory_new_list'] = explore_new_list(primary)
    # Fixed controls, no truncation and no available link.
    for row in records:
        assert all(0 < row['finish_'+k] < 12000 for k in 'ABC')
    result['controls'] = dict(full_window_ms=12000, full_window_errors_each=0,
                              zero_window_errors_each=RUNS, seed=SEED, trials_per_codec=RUNS)
    (OUT/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result['gzip'], indent=2))


if __name__ == '__main__':
    main()
