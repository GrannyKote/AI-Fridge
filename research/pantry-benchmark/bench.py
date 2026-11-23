import argparse
import csv
import ctypes
import http.client
import json
import math
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "backend"))

from fastapi import FastAPI
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app import models
from app.database import Base, get_session
from app.routers.pantry import router
from app.services import stats
from dataset import seed
from variants import (
    EVENTS, SCHEMA, install, products_statement, usage_params, usage_statement,
)

SIZES = (10000, 100000, 500000)
MODES = ("A", "B", "C")
PROFILES = {"90-10": 0.10, "70-30": 0.30}
KINDS = ("pantry", "usage", "consumption", "waste")
OUT = ROOT / "results"
HTTP_PORT = 55438


def engine_for(admin, name):
    return create_engine(make_url(admin).set(database=name), pool_size=10)


def prepare(admin, size, mode):
    name = f"fridge_bench_{size}_{mode.lower()}"
    maintenance = create_engine(admin, isolation_level="AUTOCOMMIT")
    try:
        with maintenance.connect() as conn:
            conn.exec_driver_sql(f"CREATE DATABASE {name}")
    finally:
        maintenance.dispose()
    db = engine_for(admin, name)
    with db.begin() as conn:
        conn.exec_driver_sql(f"CREATE SCHEMA {SCHEMA}")
        Base.metadata.create_all(conn)
        seed(conn, size)
        if mode != "A":
            for index, event in enumerate(EVENTS):
                conn.exec_driver_sql(f"""
                    CREATE INDEX bench_lot_time_{index} ON {SCHEMA}.{event}
                        (id_user_group_product, date_time);
                    CREATE INDEX bench_time_{index} ON {SCHEMA}.{event} (date_time);
                """)
            conn.exec_driver_sql(f"""
                CREATE INDEX bench_group ON {SCHEMA}.user_group_product (id_user_group);
                CREATE INDEX bench_open ON {SCHEMA}.user_group_product (id_user_group, best_before, id)
                    WHERE is_over IS NOT TRUE AND is_deleted IS NOT TRUE;
            """)
        if mode == "C":
            conn.exec_driver_sql((ROOT / "projection.sql").read_text(encoding="utf-8-sig"))
            sums = " UNION ALL ".join(
                f"SELECT id_user_group_product lot_id, {k} kind, quantity, date_time FROM {SCHEMA}.{event}"
                for k, event in enumerate(EVENTS)
            )
            conn.exec_driver_sql(f"""
                INSERT INTO {SCHEMA}.lot_balance
                SELECT lot_id, coalesce(sum(quantity) FILTER (WHERE kind = 0), 0),
                               coalesce(sum(quantity) FILTER (WHERE kind = 1), 0)
                FROM ({sums}) e GROUP BY lot_id;
                INSERT INTO {SCHEMA}.hourly_usage
                SELECT lot_id, kind, date_trunc('hour', date_time), sum(quantity), count(*)
                FROM ({sums}) e GROUP BY 1, 2, 3;
            """)
        conn.exec_driver_sql("ANALYZE")
    return db, name


def process_metrics():
    if sys.platform == "win32":
        class Counters(ctypes.Structure):
            _fields_ = [("size", ctypes.c_uint32), ("faults", ctypes.c_uint32),
                        ("peak", ctypes.c_size_t), ("rss", ctypes.c_size_t),
                        ("others", ctypes.c_size_t * 6)]

        process = ctypes.windll.kernel32.GetCurrentProcess
        process.restype = ctypes.c_void_p
        counters = Counters()
        counters.size = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(process()), ctypes.byref(counters), counters.size
        ):
            raise ctypes.WinError()
        peak = counters.peak
        rss = counters.rss
    else:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak *= 1 if sys.platform == "darwin" else 1024
        rss = peak
    return {"cpu_s": time.process_time(), "rss_bytes": rss, "peak_rss_bytes": peak}


def serve(name, mode):
    import uvicorn
    db = engine_for(os.environ["PANTRY_BENCH_ADMIN"], name)
    install()
    app = FastAPI()
    app.include_router(router)

    def get_benchmark_session():
        with Session(db, autoflush=False, expire_on_commit=False, info={"mode": mode}) as session:
            yield session

    app.dependency_overrides[get_session] = get_benchmark_session
    app.get("/metrics")(process_metrics)
    uvicorn.run(app, host="127.0.0.1", port=HTTP_PORT, log_level="warning", access_log=False)


def request(connection, path, payload=None):
    before = time.perf_counter()
    connection.request("GET" if payload is None else "POST", path,
                       None if payload is None else json.dumps(payload),
                       {} if payload is None else {"Content-Type": "application/json"})
    response = connection.getresponse()
    content = response.read()
    return response.status, (time.perf_counter() - before) * 1000, content


def get(path):
    connection = http.client.HTTPConnection("127.0.0.1", HTTP_PORT, timeout=120)
    try:
        status, _, body = request(connection, path)
        if status != 200:
            raise RuntimeError((status, body[:500]))
        return json.loads(body)
    finally:
        connection.close()


@contextmanager
def server(admin, name, mode):
    process = subprocess.Popen(
        [sys.executable, str(__file__), "serve", name, mode],
        env={**os.environ, "PANTRY_BENCH_ADMIN": admin},
    )
    try:
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError(f"API process exited: {process.returncode}")
            try:
                get("/metrics")
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("API did not start")
        yield
    finally:
        process.terminate()
        process.wait(timeout=15)


def canonical(value):
    value["products"].sort(key=lambda item: item["name"])
    value["categories"].sort(key=lambda item: item["id"])
    return value


def capture_snapshot():
    return {p: canonical(get(f"/api/groups/1/usage?period={p}")) for p in stats.PERIOD_DAYS} | {
        "pantry": get("/api/groups/1/products")
    }


def explain(engine, mode, size):
    def plan(session, label, statement, params=None):
        compiled = statement.compile(dialect=engine.dialect, compile_kwargs={"literal_binds": True})
        sql = "EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS) " + str(compiled)
        rows = session.execute(text(sql), params or {})
        return label + "\n" + "\n".join(row[0] for row in rows)

    with Session(engine, info={"mode": mode}) as s:
        chunks = [plan(s, "PANTRY", products_statement(s, 1))]
        if mode == "A":
            # Capture exactly the two SELECTs produced by the baseline service.
            from unittest.mock import Mock
            proxy = Mock()
            for kind in (models.UserGroupProductConsumption, models.UserGroupProductWaste):
                proxy.reset_mock()
                stats._fetch(proxy, kind, 1, usage_params(1, "year")["start"])
                chunks.append(plan(s, kind.__tablename__, proxy.execute.call_args.args[0]))
        else:
            for period in ("day", "year"):
                statement = usage_statement(s, period)
                rows = s.execute(
                    text("EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS) " + statement.text),
                    usage_params(1, period),
                )
                chunks.append(period.upper() + "\n" + "\n".join(r[0] for r in rows))
        with engine.connect() as conn:
            tx = conn.begin()
            try:
                for event in EVENTS:
                    q = f"""EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS)
                        INSERT INTO {SCHEMA}.{event}
                            (id_user_group_product, quantity, date_time)
                        VALUES (1001, 0.125, CAST(:stamp AS timestamp))"""
                    rows = conn.execute(text(q), {"stamp": "2026-01-01 12:17:33"})
                    chunks.append("INSERT " + event + "\n" + "\n".join(r[0] for r in rows))
            finally:
                tx.rollback()
    (OUT / "plans" / f"{size}-{mode}.txt").write_text("\n\n".join(chunks), encoding="utf-8")


def run_requests(profile, repeat, count, workers):
    reads = int(round(count * (1 - PROFILES[profile])))
    mix = [("pantry", "usage")[i % 2] for i in range(reads)]
    mix += [("consumption", "waste")[i % 2] for i in range(count - reads)]
    random.Random(573 + repeat).shuffle(mix)

    def worker(worker_id):
        connection = http.client.HTTPConnection("127.0.0.1", HTTP_PORT, timeout=120)
        try:
            for i in range(worker_id, count, workers):
                kind = mix[i]
                base = "/api/groups/1"
                payload = None
                if kind == "pantry":
                    path = f"{base}/products"
                elif kind == "usage":
                    path = f"{base}/usage?period=year"
                else:
                    # Distinct target lots; writes have exactly representable, unique quantities.
                    path = f"{base}/products/{1001 + worker_id}/{kind}"
                    code = (10000 if profile == "70-30" else 0) + repeat * 1000 + i
                    payload = {"quantity": (65536 + code) / 65536}
                    if kind == "waste":
                        payload["reason"] = "spoiled"
                try:
                    status, ms, body = request(connection, path, payload)
                except (OSError, http.client.HTTPException) as error:
                    yield {"kind": kind, "status": 0, "ms": None, "error": repr(error),
                           "quantity": payload["quantity"] if payload else None}
                    continue
                yield {"kind": kind, "status": status, "ms": ms,
                       "error": body[:200].decode(errors="replace") if status >= 400 else "",
                       "quantity": payload["quantity"] if payload else None}
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [row for rows in pool.map(lambda i: list(worker(i)), range(workers)) for row in rows]


def db_counts(engine):
    with engine.connect() as conn:
        return dict(conn.execute(text("""
            SELECT 'blks_read', blks_read FROM pg_stat_database WHERE datname = current_database()
            UNION ALL SELECT 'blks_hit', blks_hit FROM pg_stat_database WHERE datname = current_database()
            UNION ALL SELECT 'temp_bytes', temp_bytes FROM pg_stat_database WHERE datname = current_database()
        """)).all())


def check_history(engine, size, measured):
    expected = defaultdict(list)
    for row in measured:
        if row["kind"] in KINDS[2:] and row["status"] == 201:
            expected[row["kind"]].append(str(row["quantity"]))
    lost, unexpected, seeded = 0, 0, 0
    from decimal import Decimal
    with engine.connect() as conn:
        for kind, event in zip(KINDS[2:], EVENTS):
            recorded = Counter(conn.execute(text(f"""
                SELECT quantity FROM {SCHEMA}.{event} WHERE id > :max_id
            """), {"max_id": size // 2}).scalars())
            expected_counts = Counter(Decimal(x) for x in expected[kind])
            seeded += conn.scalar(text(f"SELECT count(*) FROM {SCHEMA}.{event} WHERE id <= :max_id"),
                                  {"max_id": size // 2})
            lost += sum((expected_counts - recorded).values())
            unexpected += sum((recorded - expected_counts).values())
    return {"seeded_count_after_load": seeded, "lost": lost, "unexpected_or_duplicate": unexpected}


def race():
    barrier = __import__("threading").Barrier(4)

    def attempt(_):
        conn = http.client.HTTPConnection("127.0.0.1", HTTP_PORT, timeout=120)
        try:
            barrier.wait()
            return request(conn, "/api/groups/1/products/1999/consumption", {"quantity": 1})[0]
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        return sorted(pool.map(attempt, range(4)))


def projection_audit(engine, mode):
    events = " UNION ALL ".join(
        f"SELECT id_user_group_product lot_id, {i} kind, quantity, date_time FROM {SCHEMA}.{name}"
        for i, name in enumerate(EVENTS)
    )
    with engine.connect() as conn:
        counted = conn.scalar(text(f"SELECT count(*) FROM ({events}) e WHERE lot_id = 1999"))
        answer = {"race_events": counted}
        if mode != "C":
            return answer
        for table, columns, expected in (
            ("lot_balance", "lot_id, consumed, wasted", """SELECT lot_id,
                coalesce(sum(quantity) FILTER(WHERE kind=0),0),
                coalesce(sum(quantity) FILTER(WHERE kind=1),0) FROM e GROUP BY 1"""),
            ("hourly_usage", "lot_id, kind, hour, quantity, entries", """SELECT lot_id, kind,
                date_trunc('hour', date_time), sum(quantity), count(*) FROM e GROUP BY 1,2,3"""),
        ):
            answer[table + "_mismatches"] = conn.scalar(text(f"""
                WITH e AS ({events}), expected AS ({expected}),
                actual AS (SELECT {columns} FROM {SCHEMA}.{table})
                SELECT count(*) FROM ((SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
                  UNION ALL (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)) d
            """))
    return answer


def compare_live(engine, mode):
    from app.services import stats as service
    from variants import ORIGINAL_USAGE, BenchmarkClock, usage
    service.datetime = BenchmarkClock
    with Session(engine, info={"mode": mode}) as session:
        return {period: canonical(usage(session, 1, period)) == canonical(ORIGINAL_USAGE(session, 1, period))
                for period in service.PERIOD_DAYS}


def percentile(values, p):
    keys = sorted(values)
    return round(keys[math.ceil(p * len(keys)) - 1], 3) if keys else None


def dump_csv(filename, rows):
    with (OUT / filename).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(records):
    groups = defaultdict(list)
    for row in records:
        groups[tuple(row[k] for k in ("size", "profile", "mode", "kind"))].append(row)
    summary = []
    for (size, profile, mode, kind), rows in sorted(groups.items()):
        values = [r["ms"] for r in rows if 200 <= r["status"] < 300]
        summary.append({"size": size, "profile": profile, "mode": mode, "kind": kind,
                        "n": len(rows), "errors": len(rows) - len(values),
                        **{f"p{int(p*100)}_ms": percentile(values,p) for p in (.50,.95,.99)}})
    baseline = {(r["size"], r["profile"], r["kind"]): r["p95_ms"]
                for r in summary if r["mode"] == "A"}
    for row in summary:
        ref = baseline.get((row["size"], row["profile"], row["kind"]))
        row["p95_reduction_pct"] = round(100 * (1 - row["p95_ms"] / ref), 2) if ref and row["p95_ms"] else None
    return summary


def run(args):
    admin = os.environ["PANTRY_BENCH_ADMIN"]
    OUT.mkdir(exist_ok=True)
    (OUT / "plans").mkdir(exist_ok=True)
    records, resources, integrity = [], [], []
    for size in args.sizes:
        reference = None
        points = {}
        for mode in MODES:
            print(f"Preparing {size} {mode}", flush=True)
            points[mode] = prepare(admin, size, mode)
        for mode, (db, name) in points.items():
            explain(db, mode, size)
            with server(admin, name, mode):
                snapshot = capture_snapshot()
                if mode == "A":
                    reference = snapshot
                checks = {key: val == reference[key] for key, val in snapshot.items()}
            assert all(checks.values()), (size, mode, checks)
            integrity.append({"size": size, "mode": mode, "initial_equivalence": checks})
        by_mode = defaultdict(list)
        for repeat in range(1, args.repeats + 1):
            for profile in PROFILES:
                order = MODES if repeat % 2 else tuple(reversed(MODES))
                for mode in order:
                    db, name = points[mode]
                    print(f"Load {size} {mode} {profile} repeat {repeat}", flush=True)
                    with server(admin, name, mode):
                        get("/api/groups/1/products")
                        get("/api/groups/1/usage?period=year")
                        before = get("/metrics")
                        db_before = db_counts(db)
                        t0 = time.perf_counter()
                        rows = run_requests(profile, repeat, args.requests, args.workers)
                        wall = time.perf_counter() - t0
                        after = get("/metrics")
                        time.sleep(1.1)
                        db_after = db_counts(db)
                    shared = {"size": size, "profile": profile, "mode": mode, "repeat": repeat}
                    records.extend(shared | row for row in rows)
                    by_mode[mode].extend(rows)
                    resources.append(shared | {"wall_s": round(wall, 3),
                        "api_cpu_s": round(after["cpu_s"] - before["cpu_s"], 5),
                        "api_peak_rss_mib": round(after["peak_rss_bytes"] / 2**20, 2),
                        "api_rss_before_load_mib": round(before["rss_bytes"] / 2**20, 2),
                        **{k: db_after[k] - db_before[k] for k in db_before}})
                    dump_csv("requests.csv", records)
                    dump_csv("resources.csv", resources)
        for info in integrity[-3:]:
            mode = info["mode"]
            db, name = points[mode]
            info.update(check_history(db, size, by_mode[mode]))
            with server(admin, name, mode):
                info["race_http_statuses"] = race()
            info.update(projection_audit(db, mode))
            info["after_race_usage_equivalence"] = compare_live(db, mode)
            db.dispose()
        (OUT / "integrity.json").write_text(json.dumps(integrity, indent=2), encoding="utf-8")
        dump_csv("metrics.csv", summarize(records))
    print("Benchmark complete.", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve(sys.argv[2], sys.argv[3])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--sizes", type=int, nargs="+", default=SIZES)
        parser.add_argument("--requests", type=int, default=160)
        parser.add_argument("--repeats", type=int, default=2)
        parser.add_argument("--workers", type=int, default=4, choices=range(1, 13))
        run(parser.parse_args())
