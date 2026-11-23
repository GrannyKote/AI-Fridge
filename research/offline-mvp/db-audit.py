"""Install or export transaction audit data in the disposable Playwright schema."""
import json
from pathlib import Path
import re
import sys

from app.config import settings
from app.database import engine


schema = settings.db_schema
assert re.fullmatch(r"e2e_[0-9a-f]{32}", schema), schema
with engine.begin() as connection:
    if sys.argv[1] == "install":
        connection.exec_driver_sql(f"""
            CREATE TABLE {schema}.experiment_audit (
                group_id integer NOT NULL, item_id integer NOT NULL, event text NOT NULL,
                happened_at timestamptz NOT NULL DEFAULT clock_timestamp()
            );
            CREATE FUNCTION {schema}.audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                INSERT INTO {schema}.experiment_audit(group_id, item_id, event)
                VALUES (NEW.id_user_group, NEW.id, TG_ARGV[0]);
                RETURN NEW;
            END
            $$;
            CREATE TRIGGER audit_quantity AFTER UPDATE OF quantity ON {schema}.user_group_product
                FOR EACH ROW EXECUTE FUNCTION {schema}.audit_mutation('quantity');
            CREATE TRIGGER audit_checkout AFTER UPDATE OF actual_date ON {schema}.user_group_purchase
                FOR EACH ROW WHEN (NEW.actual_date IS NOT NULL)
                EXECUTE FUNCTION {schema}.audit_mutation('checkout');
            CREATE TRIGGER audit_purchased AFTER UPDATE OF is_purchased ON {schema}.user_group_purchase_product
                FOR EACH ROW WHEN (NEW.is_purchased)
                EXECUTE FUNCTION {schema}.audit_mutation('purchased');
        """)
    else:
        assert sys.argv[1] == "export"
        data = {}
        for key, query in {
            "mutations": f"SELECT * FROM {schema}.experiment_audit ORDER BY happened_at",
            "idempotency": f"SELECT user_id, operation_id, status_code FROM {schema}.offline_operation",
        }.items():
            data[key] = [dict(row) for row in connection.exec_driver_sql(query).mappings()]
        Path(sys.argv[2]).write_text(json.dumps(data, default=str), encoding="utf-8")
