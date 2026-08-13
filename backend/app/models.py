from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .config import settings
from .database import Base

SCHEMA = settings.db_schema


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(256), nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)


# В базе у user_group и user_group_user составные первичные ключи —
# (id, name) и (id, id_user_group). Для ORM достаточно колонки id: она
# заполняется из последовательности и однозначно определяет строку.
class UserGroup(Base):
    __tablename__ = "user_group"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)


class UserGroupUser(Base):
    __tablename__ = "user_group_user"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user: Mapped[int] = mapped_column(Integer, nullable=False)
    id_user_group: Mapped[int] = mapped_column(Integer, nullable=False)
