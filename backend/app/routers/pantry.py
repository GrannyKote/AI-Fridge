from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..dependencies import current_user_id
from ..schemas import (
    CategoryOut,
    ConsumptionCreate,
    PantryItemCreate,
    PantryItemOut,
    PantryItemUpdate,
    PantryMoveCreate,
    PlaceOut,
    ProductSuggestionOut,
    UnitOut,
    UsageStatsOut,
    WasteCreate,
)
from ..services import catalog, pantry, stats

router = APIRouter(prefix="/api", tags=["pantry"])


def _to_item(row) -> PantryItemOut:
    return PantryItemOut(
        id=row["id"],
        product_id=row["id_product"],
        name=catalog.capitalized_name(row["product_name"]),
        quantity=float(row["quantity"]),
        remaining=float(row["remaining"]),
        price=None if row["price"] is None else float(row["price"]),
        unit=row["unit"],
        unit_id=row["id_unit_of_measurement"],
        category_id=row["id_product_category"],
        category=row["category_name"],
        storage_place_id=row["id_storage_place"],
        storage_place=row["storage_place"],
        best_before=row["best_before"],
        first_reminder_days=row["first_reminder_days"],
        second_reminder_days=row["second_reminder_days"],
        first_reminder_shown=row["first_reminder_shown"],
        first_reminder_seen=row["first_reminder_seen"],
        second_reminder_shown=row["second_reminder_shown"],
        second_reminder_seen=row["second_reminder_seen"],
        is_consumed=bool(row["is_consumed"]),
        is_wasted=bool(row["is_wasted"]),
        is_deleted=bool(row["is_deleted"]),
        is_over=bool(row["is_over"]),
    )


@router.get("/categories", response_model=list[CategoryOut])
def categories(session: Session = Depends(get_session)) -> list[CategoryOut]:
    return [CategoryOut.model_validate(item) for item in pantry.list_categories(session)]


@router.get("/units", response_model=list[UnitOut])
def units(session: Session = Depends(get_session)) -> list[UnitOut]:
    return [UnitOut.model_validate(item) for item in pantry.list_units(session)]


@router.get("/places", response_model=list[PlaceOut])
def places(session: Session = Depends(get_session)) -> list[PlaceOut]:
    return [PlaceOut.model_validate(item) for item in pantry.list_places(session)]


@router.get("/products/search", response_model=list[ProductSuggestionOut])
def search_products(
    query: str = Query(default="", max_length=512),
    limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_session),
) -> list[ProductSuggestionOut]:
    return [
        ProductSuggestionOut(**{**row, "name": catalog.capitalized_name(row["name"])})
        for row in pantry.search_products(session, query, limit)
    ]


@router.get("/groups/{group_id}/products", response_model=list[PantryItemOut])
def products(group_id: int, session: Session = Depends(get_session)) -> list[PantryItemOut]:
    return [_to_item(row) for row in pantry.merge_lots(pantry.list_products(session, group_id))]


@router.get("/groups/{group_id}/reminders", response_model=list[PantryItemOut])
def reminders(group_id: int, session: Session = Depends(get_session)) -> list[PantryItemOut]:
    return [_to_item(row) for row in pantry.merge_lots(pantry.list_reminders(session, group_id))]


@router.post("/groups/{group_id}/reminders/seen", status_code=status.HTTP_204_NO_CONTENT)
def reminders_seen(group_id: int, session: Session = Depends(get_session)) -> None:
    pantry.mark_reminders_seen(session, group_id)


@router.post(
    "/groups/{group_id}/products",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
)
def add_product(
    group_id: int,
    payload: PantryItemCreate,
    session: Session = Depends(get_session),
    user_id: int = Depends(current_user_id),
) -> PantryItemOut:
    try:
        created = pantry.create_pantry_item(session, group_id, payload, user_id)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    return _to_item(created)


@router.patch("/groups/{group_id}/products/{item_id}", response_model=PantryItemOut)
def update_product(
    group_id: int,
    item_id: int,
    payload: PantryItemUpdate,
    session: Session = Depends(get_session),
    user_id: int = Depends(current_user_id),
) -> PantryItemOut:
    try:
        updated = pantry.update_pantry_item(session, group_id, item_id, payload, user_id)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Продукт не найден")

    return _to_item(updated)


@router.post("/groups/{group_id}/products/move", response_model=list[PantryItemOut])
def move_products(
    group_id: int,
    payload: PantryMoveCreate,
    session: Session = Depends(get_session),
) -> list[PantryItemOut]:
    try:
        updated = pantry.move_storage_places(
            session, group_id, payload.item_ids, payload.storage_place_id
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Продукты не найдены")

    return [_to_item(row) for row in updated]


@router.post(
    "/groups/{group_id}/products/{item_id}/consumption",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
)
def consume_product(
    group_id: int,
    item_id: int,
    payload: ConsumptionCreate,
    session: Session = Depends(get_session),
) -> PantryItemOut:
    try:
        updated = pantry.consume_product(session, group_id, item_id, payload.quantity)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Продукт не найден")

    return _to_item(updated)


@router.get("/groups/{group_id}/usage", response_model=UsageStatsOut)
def usage_stats(
    group_id: int,
    period: Literal["day", "week", "month", "quarter", "year"] = "week",
    session: Session = Depends(get_session),
) -> UsageStatsOut:
    return UsageStatsOut(**stats.usage(session, group_id, period))


@router.post(
    "/groups/{group_id}/products/{item_id}/waste",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
)
def waste_product(
    group_id: int,
    item_id: int,
    payload: WasteCreate,
    session: Session = Depends(get_session),
) -> PantryItemOut:
    try:
        updated = pantry.waste_product(
            session, group_id, item_id, payload.reason, payload.quantity
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Продукт не найден")

    return _to_item(updated)
