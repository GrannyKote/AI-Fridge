"""Deterministic synthetic pantry data. No application database is accessed."""
from variants import EVENTS, NOW, SCHEMA


def seed(connection, size):
    connection.exec_driver_sql(f"""
        INSERT INTO {SCHEMA}.product_category(id, name)
            SELECT i, 'Category ' || i FROM generate_series(1, 4) i;
        INSERT INTO {SCHEMA}." unit_of_measurement"(id, name) VALUES (1, 'unit');
        INSERT INTO {SCHEMA}.storage_place(id, name) VALUES (1, 'Shelf');
        INSERT INTO {SCHEMA}.user_group_product
            (id, id_user_group, id_product, product_name, id_unit_of_measurement,
             quantity, best_before, id_product_category, "Id_storage_place", is_over, is_deleted)
        SELECT g * 1000 + l, g, (l - 1) %% 12 + 1, 'Product ' || ((l - 1) %% 12 + 1),
               1, 100000, date '2026-01-02' + ((l - 1) / 12),
               (l - 1) %% 4 + 1, 1, l > 18, false
        FROM generate_series(1, 4) g CROSS JOIN generate_series(1, 96) l;
        INSERT INTO {SCHEMA}.user_group_product
            (id, id_user_group, id_product, product_name, id_unit_of_measurement,
             quantity, best_before, id_product_category, "Id_storage_place")
        VALUES (1999, 1, 99, 'Race', 1, 1, '2026-03-01', 1, 1);
    """)
    for kind, event in enumerate(EVENTS):
        connection.exec_driver_sql(f"""
            INSERT INTO {SCHEMA}.{event}(id_user_group_product, quantity, date_time)
            SELECT (CASE WHEN i %% 10 < 5 THEN 1 ELSE 2 + i %% 3 END) * 1000
                   + 1 + (hashint4(i * 2 + {kind})::bigint & 2147483647) %% 96,
                   (1 + i %% 4)::numeric / 4,
                   CAST(%s AS timestamp)
                   - ((hashint4(i * 5 + {kind})::bigint & 2147483647) %% 380)
                        * interval '1 day'
                   - ((hashint4(i * 13 + {kind})::bigint & 2147483647) %% 6)
                        * interval '1 hour'
                   - (i %% 17) * interval '1 minute'
            FROM generate_series(1, %s) i
        """, (NOW, size // 2 - 6))
        connection.exec_driver_sql(f"""
            INSERT INTO {SCHEMA}.{event}(id_user_group_product, quantity, date_time)
            SELECT 1001, 0.25, CAST(%s AS timestamp) + delta
            FROM unnest(ARRAY[interval '-365 days', interval '-1 day',
                interval '-22 hours', interval '-22 hours 0.000001 seconds',
                interval '0', interval '1 hour']) delta
        """, (NOW,))
