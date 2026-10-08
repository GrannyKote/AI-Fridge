"""Убирает лишние строки в alembic_version (после stamp/restore бывает несколько head)."""
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings


def main() -> int:
    schema = settings.db_schema
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(f'SELECT version_num FROM "{schema}".alembic_version ORDER BY version_num')
            ).fetchall()
    except SQLAlchemyError as error:
        # Пустая база: схема или alembic_version ещё не созданы.
        message = str(error).lower()
        if "does not exist" in message or "undefinedtable" in message:
            return 0
        print(error, file=sys.stderr, flush=True)
        return 1

    versions = [row[0] for row in rows if row[0]]
    if len(versions) <= 1:
        return 0

    keep = max(versions)
    drop = [version for version in versions if version != keep]
    print(
        f"alembic_version: found {len(versions)} rows {versions!r}; "
        f"keeping {keep!r}, removing {drop!r}",
        flush=True,
    )

    try:
        with engine.begin() as connection:
            for version in drop:
                connection.execute(
                    text(f'DELETE FROM "{schema}".alembic_version WHERE version_num = :v'),
                    {"v": version},
                )
    except SQLAlchemyError as error:
        print(error, file=sys.stderr, flush=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
