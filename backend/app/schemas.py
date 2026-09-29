from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    role: str = "user"
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


class ShelfLifeOut(BaseModel):
    name: str
    shelf_life_days: int


class FeedbackIn(BaseModel):
    user_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Напишите сообщение")
        return text


class FeedbackOut(BaseModel):
    status: str


class FeedbackPhotoOut(BaseModel):
    id: int


class FeedbackEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    message: str
    date_time: datetime
    photos: list[FeedbackPhotoOut]


class ShelfLifeIn(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    shelf_life_days: int = Field(gt=0, le=3650)


class PantryItemOut(BaseModel):
    id: int
    name: str
    quantity: float
    remaining: float
    unit: str | None = None
    category_id: int | None = None
    category: str | None = None
    storage_place_id: int | None = None
    storage_place: str | None = None
    best_before: date
    purchased_on: date | None = None
    is_consumed: bool = False
    is_wasted: bool = False
    is_deleted: bool = False
    is_over: bool = False


class PantryItemUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    category: str = Field(min_length=1, max_length=512)
    unit_id: int
    quantity: float = Field(gt=0)
    best_before: date
    purchased_on: date | None = None
    storage_place_id: int


class PantryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    category: str = Field(min_length=1, max_length=512)
    unit_id: int
    quantity: float = Field(gt=0)
    best_before: date
    purchased_on: date | None = None
    storage_place_id: int | None = None
    product_id: int | None = None
    user_id: int | None = None


class ConsumptionCreate(BaseModel):
    quantity: float = Field(gt=0)


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


class PlanDateUpdate(BaseModel):
    plan_date: date


class PurchaseHeaderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_date: date | None = None


class CheckoutItem(BaseModel):
    id: int
    quantity: float = Field(gt=0)
    best_before: date
    storage_place_id: int


class PurchaseCheckout(BaseModel):
    items: list[CheckoutItem] = Field(min_length=1)
    user_id: int | None = None
    purchased_on: date | None = None


class NewsIn(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Заполните поле")
        return text


class NewsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    date_time: datetime


class WindowCounts(BaseModel):
    day: int
    week: int
    month: int


class UploadStatsOut(BaseModel):
    products: WindowCounts
    users: WindowCounts
