from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LOGIN_PATTERN = r"^[a-zA-Z0-9._-]+$"


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=20, pattern=LOGIN_PATTERN)
    password: str = Field(min_length=6, max_length=256)


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    groups: list[GroupOut] = []


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductSuggestionOut(BaseModel):
    id: int
    name: str
    category_id: int | None = None
    category: str | None = None


class PantryItemOut(BaseModel):
    id: int
    name: str
    quantity: float
    remaining: float
    unit: str | None = None
    category_id: int | None = None
    category: str | None = None
    best_before: date
    is_consumed: bool = False
    is_wasted: bool = False
    is_deleted: bool = False
    is_over: bool = False


class PantryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    category: str = Field(min_length=1, max_length=512)
    unit_id: int
    quantity: float = Field(gt=0)
    best_before: date
    product_id: int | None = None


class ConsumptionCreate(BaseModel):
    quantity: float = Field(gt=0)


class CategoryUsageOut(BaseModel):
    id: int | None = None
    name: str
    quantity: float
    unit: str | None = None


class ProductUsageOut(BaseModel):
    name: str
    category: str | None = None
    category_id: int | None = None
    unit: str | None = None
    entries: int
    total: float
    per_day: float
    buckets: list[float]


class ConsumptionStatsOut(BaseModel):
    period: str
    period_days: int
    categories: list[CategoryUsageOut]
    products: list[ProductUsageOut]


class WasteCreate(BaseModel):
    # spoiled — продукт испортился, mistake — запись добавлена ошибочно.
    reason: Literal["spoiled", "mistake"]
    quantity: float | None = Field(default=None, gt=0)
