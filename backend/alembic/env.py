from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text

from app import models  # noqa: F401  — импорт регистрирует таблицы в Base.metadata
from app.config import settings
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
SCHEMA = settings.db_schema


def include_name(name: str | None, type_: str, parent_names: dict) -> bool:
    """Автогенерация смотрит только на схему проекта, остальные игнорирует."""
    if type_ == "schema":
        return name == SCHEMA
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
        version_table_schema=SCHEMA,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Строка подключения берётся из настроек приложения, а не из alembic.ini,
    # чтобы пароль с символом % не ломал разбор ini-файла.
    engine = create_engine(settings.database_url, poolclass=pool.NullPool)

    with engine.connect() as connection:
        # Таблица alembic_version живёт в схеме проекта, поэтому схема должна
        # существовать до того, как Alembic начнёт читать историю ревизий.
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            version_table_schema=SCHEMA,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
