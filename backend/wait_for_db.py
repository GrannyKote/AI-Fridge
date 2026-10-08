"""Ждёт доступности PostgreSQL перед alembic (postgres healthy ≠ готов принять SQL)."""
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings


def _target_label() -> str:
    return (
        f"{settings.postgres_user}@{settings.postgres_host or '?'}"
        f":{settings.postgres_port}/{settings.postgres_db}"
    )


def main() -> int:
    attempts = 30
    delay_seconds = 2

    print(f"Waiting for PostgreSQL ({_target_label()})...", flush=True)

    last_error: Exception | None = None
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("select 1"))
            print("PostgreSQL is ready.", flush=True)
            return 0
        except SQLAlchemyError as error:
            last_error = error
            print(f"  attempt {attempt}/{attempts}: {error}", flush=True)
            time.sleep(delay_seconds)

    print(f"ERROR: PostgreSQL not reachable after {attempts} attempts.", file=sys.stderr, flush=True)
    if last_error is not None:
        print(last_error, file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
