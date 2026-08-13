from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..schemas import (
    CategoryOut,
    ConsumptionCreate,
    PantryItemCreate,
    PantryItemOut,
    ProductSuggestionOut,
    UnitOut,
    WasteCreate,
)
from ..services import pantry

router = APIRouter(prefix="/api", tags=["pantry"])


def _to_item(row) -> PantryItemOut:
    return PantryItemOut(
        id=row["id"],
        name=row["product_name"],
        quantity=float(row["quantity"]),
        remaining=float(row["remaining"]),
        unit=row["unit"],
        category_id=row["id_product_category"],
        category=row["category_name"],
        best_before=row["best_before"],
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


@router.get("/products/search", response_model=list[ProductSuggestionOut])
def search_products(
    query: str = Query(default="", max_length=512),
    limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_session),
) -> list[ProductSuggestionOut]:
    return [
        ProductSuggestionOut(**row) for row in pantry.search_products(session, query, limit)
    ]


@router.get("/groups/{group_id}/products", response_model=list[PantryItemOut])
def products(group_id: int, session: Session = Depends(get_session)) -> list[PantryItemOut]:
    return [_to_item(row) for row in pantry.list_products(session, group_id)]


@router.post(
    "/groups/{group_id}/products",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
)
def add_product(
    group_id: int,
    payload: PantryItemCreate,
    session: Session = Depends(get_session),
) -> PantryItemOut:
    try:
        created = pantry.create_pantry_item(session, group_id, payload)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    return _to_item(created)


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
