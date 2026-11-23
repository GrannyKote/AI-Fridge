"""Additional integrity checks on completed, isolated experiment databases."""
import json
import os
from statistics import median

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from bench import EVENTS, MODES, OUT, SCHEMA, SIZES, engine_for
from variants import NOW, products_statement


def inspect_seed(session, size):
    totals = {}
    for event in EVENTS:
        table = f"{SCHEMA}.{event}"
        count, fingerprint = session.execute(text(f"""
            SELECT count(*), sum(hashtextextended(to_jsonb(e)::text, 0)::numeric)
            FROM {table} e WHERE id <= :max_id
        """), {"max_id": size // 2}).one()
        totals[event] = {"count": count, "fingerprint": str(fingerprint)}
    return totals


def compare_pantry(session, mode):
    observed = session.execute(products_statement(session, 1)).mappings().all()
    session.info["mode"] = "A"
    expected = session.execute(products_statement(session, 1)).mappings().all()
    session.info["mode"] = mode
    return len([1 for left, right in zip(observed, expected) if left != right]) + abs(len(observed) - len(expected))


def verify_write_rules(session):
    event = f"{SCHEMA}.{EVENTS[0]}"
    at = {"now": NOW}
    dependent_queries = (
        f"SELECT count(*) FROM {event}",
        f"SELECT consumed, wasted FROM {SCHEMA}.lot_balance WHERE lot_id = 1001",
        f"""SELECT quantity, entries FROM {SCHEMA}.hourly_usage WHERE lot_id = 1001
            AND kind = 0 AND hour = date_trunc('hour', CAST(:now AS timestamp))""",
    )

    def dependent_state():
        return [session.execute(text(query), at).all() for query in dependent_queries]

    before = dependent_state()
    initial = session.execute(products_statement(session, 1, 1001)).mappings().one()["remaining"]
    adjustment = session.begin_nested()
    session.execute(text(f"UPDATE {SCHEMA}.user_group_product SET quantity = quantity + 3 WHERE id = 1001"))
    adjusted = session.execute(products_statement(session, 1, 1001)).mappings().one()["remaining"]
    adjustment.rollback()

    trial = session.begin_nested()
    session.execute(text(f"""
        INSERT INTO {event} (id_user_group_product, quantity, date_time) VALUES (1001, 0.25, :now)
    """), at)
    during = dependent_state()
    trial.rollback()
    immutable = {}
    for action, statement in {
        "update": f"UPDATE {event} SET quantity = 5 WHERE id = 1",
        "delete": f"DELETE FROM {event} WHERE id = 1",
        "truncate": f"TRUNCATE {event}",
    }.items():
        try:
            with session.begin_nested() as operation:
                session.execute(text(statement))
                operation.rollback()
        except DBAPIError as error:
            immutable[action] = "history is append-only" in str(error)
        else:
            immutable[action] = False
    return {
        "quantity_adjustment_updates_visible_remaining": adjusted - initial == 3,
        "event_and_projection_change_before_rollback": (
            during[0][0][0] == before[0][0][0] + 1
            and during[1][0][0] - before[1][0][0] == 0.25
            and during[2][0][0] - before[2][0][0] == 0.25
            and during[2][0][1] == before[2][0][1] + 1
        ),
        "event_and_projections_restored_by_rollback": before == dependent_state(),
        "history_mutation_rejected": immutable,
    }


def measure_write_wal(session):
    result = {}
    for event in EVENTS:
        samples = []
        for _ in range(7):
            trial = session.begin_nested()
            before = session.scalar(text("SELECT pg_current_wal_insert_lsn()"))
            session.execute(text(f"""
                INSERT INTO {SCHEMA}.{event} (id_user_group_product, quantity, date_time)
                VALUES (1001, 0.25, :stamp)
            """), {"stamp": NOW})
            samples.append(int(session.scalar(text("""
                SELECT pg_wal_lsn_diff(pg_current_wal_insert_lsn(), CAST(:before AS pg_lsn))
            """), {"before": before})))
            trial.rollback()
        result[event] = int(median(samples[2:]))
    return result


def main():
    admin = os.environ["PANTRY_BENCH_ADMIN"]
    report = []
    for size in SIZES:
        reference = None
        for mode in MODES:
            engine = engine_for(admin, f"fridge_bench_{size}_{mode.lower()}")
            with Session(engine, info={"mode": mode}) as session:
                fingerprint = inspect_seed(session, size)
                if mode == "A":
                    reference = fingerprint
                race_remaining = session.execute(products_statement(session, 1, 1999)).mappings().one()["remaining"]
                row = {"size": size, "mode": mode, "seed_matches_baseline": fingerprint == reference,
                       "seed": fingerprint, "open_lot_mismatches": compare_pantry(session, mode),
                       "race_remaining": str(race_remaining),
                       "wal_lsn_delta_bytes_per_insert_median": measure_write_wal(session)}
                if mode == "C":
                    row.update(verify_write_rules(session))
                report.append(row)
            engine.dispose()
    (OUT / "transaction-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
