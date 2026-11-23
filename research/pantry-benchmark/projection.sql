-- Applied only to experiment databases.
CREATE TABLE diplom_all.lot_balance (
    lot_id integer PRIMARY KEY,
    consumed numeric NOT NULL DEFAULT 0,
    wasted numeric NOT NULL DEFAULT 0
);

CREATE TABLE diplom_all.hourly_usage (
    lot_id integer NOT NULL,
    kind integer NOT NULL,
    hour timestamp NOT NULL,
    quantity numeric NOT NULL,
    entries bigint NOT NULL,
    PRIMARY KEY (lot_id, hour, kind)
);

CREATE FUNCTION diplom_all.project_event() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    event_kind integer := TG_ARGV[0]::integer;
BEGIN
    INSERT INTO diplom_all.lot_balance VALUES (
        NEW.id_user_group_product,
        CASE WHEN event_kind = 0 THEN NEW.quantity ELSE 0 END,
        CASE WHEN event_kind = 1 THEN NEW.quantity ELSE 0 END
    )
    ON CONFLICT (lot_id) DO UPDATE SET
        consumed = lot_balance.consumed + EXCLUDED.consumed,
        wasted = lot_balance.wasted + EXCLUDED.wasted;

    INSERT INTO diplom_all.hourly_usage VALUES (
        NEW.id_user_group_product, event_kind, date_trunc('hour', NEW.date_time),
        NEW.quantity, 1
    )
    ON CONFLICT (lot_id, hour, kind) DO UPDATE SET
        quantity = hourly_usage.quantity + EXCLUDED.quantity,
        entries = hourly_usage.entries + 1;
    RETURN NEW;
END;
$$;

CREATE TRIGGER project_consumption AFTER INSERT ON diplom_all.user_group_product_consumption
    FOR EACH ROW EXECUTE FUNCTION diplom_all.project_event('0');
CREATE TRIGGER project_waste AFTER INSERT ON diplom_all.user_group_product_waste
    FOR EACH ROW EXECUTE FUNCTION diplom_all.project_event('1');

CREATE FUNCTION diplom_all.reject_event_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'history is append-only';
END;
$$;
CREATE TRIGGER immutable_consumption BEFORE UPDATE OR DELETE OR TRUNCATE
    ON diplom_all.user_group_product_consumption FOR EACH STATEMENT
    EXECUTE FUNCTION diplom_all.reject_event_change();
CREATE TRIGGER immutable_waste BEFORE UPDATE OR DELETE OR TRUNCATE
    ON diplom_all.user_group_product_waste FOR EACH STATEMENT
    EXECUTE FUNCTION diplom_all.reject_event_change();
