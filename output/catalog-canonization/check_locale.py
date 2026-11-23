"""Verify that the PostgreSQL character classifier handles Cyrillic."""
import psycopg

from bench import DSN


if __name__ == "__main__":
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        print(conn.execute(
            """
            SELECT datctype, show_trgm(%s), similarity(%s, %s)
            FROM pg_database WHERE datname = current_database()
            """,
            ("молоко ваниль", "малако ваниль", "молоко ваниль"),
        ).fetchone())
