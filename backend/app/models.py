from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
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
    # Автор продукта: NULL у позиций общего справочника.
    id_user_created: Mapped[int | None] = mapped_column(Integer)
    datetime_created: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # За сколько дней до истечения срока напомнить: первое и второе напоминание.
    first_reminder_days: Mapped[int | None] = mapped_column(SmallInteger)
    second_reminder_days: Mapped[int | None] = mapped_column(SmallInteger)
    # Срок хранения продукта в днях — подсказка для best_before в кладовой.
    expires_in: Mapped[int | None] = mapped_column(SmallInteger)


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
    # Цена за всю позицию целиком, а не за единицу измерения.
    price: Mapped[Decimal | None] = mapped_column(Numeric)
    best_before: Mapped[date] = mapped_column(Date, nullable=False)
    id_product_category: Mapped[int] = mapped_column(Integer, nullable=False)
    # В базе колонка создана как "Id_storage_place".
    id_storage_place: Mapped[int | None] = mapped_column("Id_storage_place", Integer)
    is_deleted: Mapped[bool | None] = mapped_column(Boolean)
    is_consumed: Mapped[bool | None] = mapped_column(Boolean)
    is_wasted: Mapped[bool | None] = mapped_column(Boolean)
    is_over: Mapped[bool | None] = mapped_column(Boolean)
    # Когда продукт попал в список колокольчика и когда это напоминание посмотрели.
    first_reminder_shown: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_reminder_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    second_reminder_shown: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    second_reminder_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user: Mapped[int] = mapped_column(Integer, nullable=False)
    datetime_created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    feedback_text: Mapped[str | None] = mapped_column(Text)


class FeedbackItem(Base):
    __tablename__ = "feedback_item"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_feedback: Mapped[int] = mapped_column(Integer, nullable=False)
    # Сама картинка, приложенная к отзыву.
    item: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class News(Base):
    __tablename__ = "news"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user_created: Mapped[int] = mapped_column(Integer, nullable=False)
    datetime_created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    header: Mapped[str] = mapped_column(String(1024), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)


# В базе у user_news_seen составной первичный ключ (id, id_news, id_user_seen).
# Для ORM достаточно колонки id: она заполняется из последовательности.
class UserNewsSeen(Base):
    __tablename__ = "user_news_seen"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_news: Mapped[int] = mapped_column(Integer, nullable=False)
    id_user_seen: Mapped[int] = mapped_column(Integer, nullable=False)
    datetime_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
