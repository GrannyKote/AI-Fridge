from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    pool_size=10,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_session(request: Request) -> Iterator[Session]:
    connection = getattr(request.state, "offline_connection", None)
    options = {"bind": connection, "join_transaction_mode": "rollback_only"} if connection else {}
    with SessionLocal(**options) as session:
        yield session
