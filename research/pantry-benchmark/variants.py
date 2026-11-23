from datetime import datetime, timedelta

from sqlalchemy import Numeric, and_, column, func, select, table, text
from sqlalchemy.sql import SelectLabelStyle

from app.models import UserGroupProduct as Lot
from app.services import pantry, stats

SCHEMA = "diplom_all"
EVENTS = ("user_group_product_consumption", "user_group_product_waste")
NOW = datetime(2026, 1, 1, 12, 17, 33)
ORIGINAL_PRODUCTS = pantry._products_statement
ORIGINAL_TOTAL = pantry._total_of
ORIGINAL_WRITE = pantry._write_off_lot
ORIGINAL_USAGE = stats.usage
BALANCE = table(
    "lot_balance", column("lot_id"), column("consumed", Numeric),
    column("wasted", Numeric), schema=SCHEMA,
)


class BenchmarkClock(datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return NOW.astimezone(tz)
        return NOW


def products_statement(session, group_id, item_id=None):
    mode = session.info["mode"]
    statement = ORIGINAL_PRODUCTS()
    active = (Lot.is_over.is_not(True), Lot.is_deleted.is_not(True))
    filters = [Lot.id_user_group == group_id]
    filters.extend(active if item_id is None else [Lot.id == item_id])

    if mode != "A":
        if mode == "C":
            statement = statement.outerjoin(BALANCE, BALANCE.c.lot_id == Lot.id)
            consumed, wasted = BALANCE.c.consumed, BALANCE.c.wasted
        else:
            eligible = select(Lot.id).where(*filters).cte("eligible")
            sums = []
            for model in (pantry.UserGroupProductConsumption, pantry.UserGroupProductWaste):
                totals = (
                    select(model.id_user_group_product.label("lot_id"), func.sum(model.quantity).label("total"))
                    .join(eligible, eligible.c.id == model.id_user_group_product)
                    .group_by(model.id_user_group_product)
                    .subquery()
                )
                statement = statement.outerjoin(totals, totals.c.lot_id == Lot.id)
                sums.append(totals.c.total)
            consumed, wasted = sums
        remaining = Lot.quantity - func.coalesce(consumed, 0) - func.coalesce(wasted, 0)
        fields = [remaining.label("remaining") if field.key == "remaining" else field
                  for field in statement.selected_columns]
        statement = statement.with_only_columns(*fields, maintain_column_froms=True)
    statement = statement.where(*filters)
    if item_id is None:
        statement = statement.order_by(Lot.best_before, Lot.id)
    return statement


def read_lots(session, group_id):
    return session.execute(products_statement(session, group_id)).mappings().all()


def read_lot(session, group_id, item_id):
    return session.execute(products_statement(session, group_id, item_id)).mappings().first()


def total_of(session, model, item_id):
    if session.info["mode"] != "C":
        return ORIGINAL_TOTAL(session, model, item_id)
    amount = BALANCE.c.consumed if model is pantry.UserGroupProductConsumption else BALANCE.c.wasted
    return session.scalar(select(amount).where(BALANCE.c.lot_id == item_id)) or 0


def write_off(session, group_id, item_id, quantity, model):
    if session.info["mode"] == "C":
        # Serializes the read/distribute/write sequence for merged lots within one group.
        session.execute(text("SELECT pg_advisory_xact_lock(885712, :group)"), {"group": group_id})
    return ORIGINAL_WRITE(session, group_id, item_id, quantity, model)


def usage_statement(session, period):
    common = """
        WITH eligible AS (
            SELECT id, product_name, id_product_category, id_unit_of_measurement
            FROM diplom_all.user_group_product WHERE id_user_group = :group
        )
    """
    raw = " UNION ALL ".join(
        f"""SELECT e.id_user_group_product AS lot_id, {kind} AS kind,
                   e.date_time, e.quantity
            FROM {SCHEMA}.{event} e JOIN eligible l ON l.id = e.id_user_group_product
            WHERE e.date_time >= :start"""
        for kind, event in enumerate(EVENTS)
    )
    if session.info["mode"] == "B":
        source = f"""
            , pieces AS (
                SELECT lot_id, kind, quantity, 1 AS entries,
                    least(11, extract(epoch FROM
                        date_bin(CAST(:step AS interval), date_time, CAST(:start AS timestamp))
                        - CAST(:start AS timestamp)) / :seconds)::integer AS bucket
                FROM ({raw}) events
            )
        """
    else:
        source = """
            , windows AS (
                SELECT bucket,
                       CAST(:start AS timestamp) + bucket * CAST(:step AS interval) AS lo,
                       CASE WHEN bucket = 11 THEN 'infinity'::timestamp
                            ELSE CAST(:start AS timestamp) + (bucket + 1) * CAST(:step AS interval) END AS hi
                FROM generate_series(0, 11) bucket
            ), bounds AS (
                SELECT *, CASE WHEN date_trunc('hour', lo) = lo THEN lo
                               ELSE date_trunc('hour', lo) + interval '1 hour' END AS full_lo,
                       CASE WHEN isfinite(hi) THEN date_trunc('hour', hi) ELSE hi END AS full_hi
                FROM windows
            ), edges AS (
                SELECT bucket, lo, least(hi, full_lo) AS hi FROM bounds WHERE lo < least(hi, full_lo)
                UNION ALL
                SELECT bucket, greatest(lo, full_lo, full_hi), hi FROM bounds
                WHERE greatest(lo, full_lo, full_hi) < hi
            ), pieces AS (
                SELECT h.lot_id, h.kind, h.quantity, h.entries, b.bucket
                FROM bounds b JOIN diplom_all.hourly_usage h ON h.hour >= b.full_lo AND h.hour < b.full_hi
                JOIN eligible l ON l.id = h.lot_id
        """
        for kind, event in enumerate(EVENTS):
            source += f"""
                UNION ALL
                SELECT e.id_user_group_product, {kind}, e.quantity, 1, b.bucket
                FROM edges b JOIN {SCHEMA}.{event} e ON e.date_time >= b.lo AND e.date_time < b.hi
                JOIN eligible l ON l.id = e.id_user_group_product
            """
        source += ")"
    return text(common + source + """
        SELECT p.kind, p.bucket, l.product_name, l.id_product_category,
               c.name AS category, u.name AS unit, sum(p.quantity) AS quantity, sum(p.entries) AS entries
        FROM pieces p JOIN eligible l ON l.id = p.lot_id
        LEFT JOIN diplom_all.product_category c ON c.id = l.id_product_category
        LEFT JOIN diplom_all." unit_of_measurement" u ON u.id = l.id_unit_of_measurement
        GROUP BY p.kind, p.bucket, l.product_name, l.id_product_category, c.name, u.name
    """)


def usage_params(group_id, period):
    days = stats.PERIOD_DAYS[period]
    seconds = days * 7200
    return {"group": group_id, "start": NOW - timedelta(days=days),
            "step": timedelta(seconds=seconds), "seconds": seconds}


def usage(session, group_id, period):
    if session.info["mode"] == "A":
        return ORIGINAL_USAGE(session, group_id, period)
    days = stats.PERIOD_DAYS[period]
    rows = session.execute(usage_statement(session, period), usage_params(group_id, period)).mappings().all()
    kinds = ([], [])
    products = {}
    for row in rows:
        kind = row["kind"]
        kinds[kind].append(row)
        name = pantry.catalog.capitalized_name(row["product_name"])
        item = products.setdefault(name, {
            "name": name, "category": row["category"], "category_id": row["id_product_category"],
            "unit": row["unit"], "consumption": None, "waste": None,
        })
        key = ("consumption", "waste")[kind]
        if item[key] is None:
            item[key] = {"entries": 0, "total": 0, "buckets": [0] * stats.BUCKETS}
        series = item[key]
        series["entries"] += int(row["entries"])
        series["total"] += row["quantity"]
        series["buckets"][row["bucket"]] += row["quantity"]
    for item in products.values():
        for key in ("consumption", "waste"):
            series = item[key]
            if series is not None:
                series["per_day"] = stats._round(series["total"] / days)
                series["total"] = stats._round(series["total"])
                series["buckets"] = [stats._round(value) for value in series["buckets"]]
    return {"period": period, "period_days": days, "categories": stats._categories(*kinds),
            "products": sorted(products.values(), key=lambda item: sum(
                (item[k] or {}).get("total", 0) for k in ("consumption", "waste")), reverse=True)}


def install():
    pantry.datetime = BenchmarkClock
    stats.datetime = BenchmarkClock
    pantry.list_products = read_lots
    pantry.get_product = read_lot
    pantry._total_of = total_of
    pantry._write_off_lot = write_off
    stats.usage = usage
