from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LOGIN_PATTERN = r"^[a-zA-Z0-9._-]+$"


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=20, pattern=LOGIN_PATTERN)
    password: str = Field(min_length=6, max_length=256)
    user_agent: str = Field(default="", max_length=1024)


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)
    user_agent: str = Field(default="", max_length=1024)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    # JWT: клиент отдаёт его обратно в заголовке Authorization.
    token: str
    is_admin: bool = False
    groups: list[GroupOut] = []


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class PlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductSuggestionOut(BaseModel):
    id: int
    name: str
    category_id: int | None = None
    category: str | None = None
    # Срок хранения в днях: из него считается срок годности по умолчанию.
    expires_in: int | None = None


class PantryItemOut(BaseModel):
    id: int
    product_id: int | None = None
    name: str
    quantity: float
    remaining: float
    price: float | None = None
    unit: str | None = None
    unit_id: int | None = None
    category_id: int | None = None
    category: str | None = None
    storage_place_id: int | None = None
    storage_place: str | None = None
    best_before: date
    # За сколько дней до конца срока показывать продукт как «скоро испортится».
    first_reminder_days: int | None = None
    second_reminder_days: int | None = None
    first_reminder_shown: datetime | None = None
    first_reminder_seen: datetime | None = None
    second_reminder_shown: datetime | None = None
    second_reminder_seen: datetime | None = None
    is_consumed: bool = False
    is_wasted: bool = False
    is_deleted: bool = False
    is_over: bool = False


class PantryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    category: str = Field(min_length=1, max_length=512)
    unit_id: int
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, ge=0)
    best_before: date
    storage_place_id: int | None = None
    product_id: int | None = None


class PantryItemUpdate(PantryItemCreate):
    """Редактирование: quantity — текущий остаток, не изначальное количество."""


class ConsumptionCreate(BaseModel):
    quantity: float = Field(gt=0)


class PantryMoveCreate(BaseModel):
    item_ids: list[int] = Field(min_length=1)
    storage_place_id: int


class CategoryUsageOut(BaseModel):
    id: int | None = None
    name: str
    unit: str | None = None
    consumed: float
    wasted: float


class UsageSeriesOut(BaseModel):
    entries: int
    total: float
    per_day: float
    buckets: list[float]


class ProductUsageOut(BaseModel):
    name: str
    category: str | None = None
    category_id: int | None = None
    unit: str | None = None
    consumption: UsageSeriesOut | None = None
    waste: UsageSeriesOut | None = None


class UsageStatsOut(BaseModel):
    period: str
    period_days: int
    categories: list[CategoryUsageOut]
    products: list[ProductUsageOut]


class WasteCreate(BaseModel):
    # spoiled — продукт испортился, mistake — запись добавлена ошибочно.
    reason: Literal["spoiled", "mistake"]
    quantity: float | None = Field(default=None, gt=0)


class PurchaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    category: str = Field(min_length=1, max_length=512)
    unit_id: int
    quantity: float = Field(gt=0)
    product_id: int | None = None


class PurchaseOut(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str | None = None
    category_id: int | None = None
    category: str | None = None
    expires_in: int | None = None


class PlanDateUpdate(BaseModel):
    plan_date: date


class PurchaseHeaderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_date: date | None = None


class CheckoutItem(BaseModel):
    id: int
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, ge=0)
    best_before: date
    storage_place_id: int


class PurchaseCheckout(BaseModel):
    items: list[CheckoutItem] = Field(min_length=1)


class FeedbackItemOut(BaseModel):
    id: int


class FeedbackOut(BaseModel):
    id: int
    id_user: int
    datetime_created: datetime
    feedback_text: str
    items: list[FeedbackItemOut] = []


class NewsListItemOut(BaseModel):
    id: int
    header: str
    is_seen: bool = False


class NewsOut(BaseModel):
    id: int
    header: str
    body: str = ""
    is_seen: bool = False


class AdminNewsListItemOut(BaseModel):
    id: int
    header: str


class AdminNewsOut(BaseModel):
    id: int
    header: str
    body: str = ""


class AdminNewsUpdate(BaseModel):
    header: str = Field(min_length=1, max_length=1024)
    body: str = Field(default="", max_length=20000)


class AdminNewsViewerOut(BaseModel):
    login: str
    datetime_seen: datetime


class AdminFeedbackListItemOut(BaseModel):
    id: int
    login: str
    datetime_created: datetime
    text_preview: str
    is_seen: bool = False


class AdminFeedbackDetailOut(BaseModel):
    id: int
    login: str
    datetime_created: datetime
    feedback_text: str
    is_seen: bool = False
    datetime_seen: datetime | None = None
    items: list[FeedbackItemOut] = []
