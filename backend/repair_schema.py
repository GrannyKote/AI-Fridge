"""Выравнивание схемы без смены alembic_version — после каждого restore бэкапа.

  python repair_schema.py

В Docker:

  docker compose exec backend python repair_schema.py
"""
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from app.schema_repair import apply_schema_repairs
from app.config import settings


def main() -> None:
    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context) as op:
            apply_schema_repairs(op)
    print("Schema repair completed.")


if __name__ == "__main__":
    main()
