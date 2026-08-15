from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Time
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


class CreatedUser(Base):
    __tablename__ = "created_user"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str | None] = mapped_column(String(512))
    date_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=False)
    ip: Mapped[str] = mapped_column(String(256), nullable=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempt"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(512), nullable=False)
    # В базе это TIME WITH TIME ZONE, не timestamp.
    date_time: Mapped[time] = mapped_column(Time(timezone=True), nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=False)
    ip: Mapped[str] = mapped_column(String(256), nullable=False)


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


class ProductCategory(Base):
    __tablename__ = "product_category"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)


class Product(Base):
    __tablename__ = "product"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    id_product_category: Mapped[int] = mapped_column(Integer, nullable=False)


class UnitOfMeasurement(Base):
    # Имя таблицы в базе начинается с пробела, поэтому оно указано как есть.
    __tablename__ = " unit_of_measurement"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class StoragePlace(Base):
    __tablename__ = "storage_place"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class UserGroupProduct(Base):
    __tablename__ = "user_group_product"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user_group: Mapped[int] = mapped_column(Integer, nullable=False)
    id_product: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)
    id_unit_of_measurement: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    best_before: Mapped[date] = mapped_column(Date, nullable=False)
    id_product_category: Mapped[int] = mapped_column(Integer, nullable=False)
    # В базе колонка создана как "Id_storage_place".
    id_storage_place: Mapped[int | None] = mapped_column("Id_storage_place", Integer)
    is_deleted: Mapped[bool | None] = mapped_column(Boolean)
    is_consumed: Mapped[bool | None] = mapped_column(Boolean)
    is_wasted: Mapped[bool | None] = mapped_column(Boolean)
    is_over: Mapped[bool | None] = mapped_column(Boolean)


class UserGroupPurchase(Base):
    __tablename__ = "user_group_purchase"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user_group: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_date: Mapped[date | None] = mapped_column(Date)
    actual_date: Mapped[datetime | None] = mapped_column(DateTime)
    create_date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserGroupPurchaseProduct(Base):
    __tablename__ = "user_group_purchase_product"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user_group: Mapped[int] = mapped_column(Integer, nullable=False)
    id_product: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)
    id_unit_of_measurement: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    id_product_category: Mapped[int] = mapped_column(Integer, nullable=False)
    id_user_group_purchase: Mapped[int] = mapped_column(Integer, nullable=False)
    create_date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_deleted: Mapped[bool | None] = mapped_column(Boolean)
    is_purchased: Mapped[bool | None] = mapped_column(Boolean)


class UserGroupProductConsumption(Base):
    __tablename__ = "user_group_product_consumption"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user_group_product: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserGroupProductWaste(Base):
    __tablename__ = "user_group_product_waste"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user_group_product: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
