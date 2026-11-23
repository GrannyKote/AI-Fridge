from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import get_session
from ..dependencies import current_user_id
from ..offline import OfflineMutationRoute
from ..schemas import PlanDateUpdate, PurchaseCheckout, PurchaseCreate, PurchaseHeaderOut, PurchaseOut
from ..services import catalog, shopping

router = APIRouter(prefix="/api", tags=["shopping"], route_class=OfflineMutationRoute)


def _to_item(row) -> PurchaseOut:
    return PurchaseOut(
        id=row["id"],
        name=catalog.capitalized_name(row["product_name"]),
        quantity=float(row["quantity"]),
        unit=row["unit"],
        category_id=row["id_product_category"],
        category=row["category_name"],
        expires_in=row["expires_in"],
    )


@router.get("/groups/{group_id}/purchases", response_model=list[PurchaseOut])
def purchases(group_id: int, session: Session = Depends(get_session)) -> list[PurchaseOut]:
    return [_to_item(row) for row in shopping.list_purchases(session, group_id)]


@router.post(
    "/groups/{group_id}/purchases",
    response_model=PurchaseOut,
    status_code=status.HTTP_201_CREATED,
)
def add_purchase(
    group_id: int,
    payload: PurchaseCreate,
    session: Session = Depends(get_session),
    user_id: int = Depends(current_user_id),
) -> PurchaseOut:
    try:
        created = shopping.create_purchase(session, group_id, payload, user_id)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    return _to_item(created)


@router.delete(
    "/groups/{group_id}/purchases/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_purchase(
    group_id: int,
    item_id: int,
    session: Session = Depends(get_session),
) -> None:
    if not shopping.delete_purchase_product(session, group_id, item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")


@router.get("/groups/{group_id}/purchase", response_model=PurchaseHeaderOut)
def purchase_header(group_id: int, session: Session = Depends(get_session)) -> PurchaseHeaderOut:
    header = shopping.get_purchase_header(session, group_id)
    if header is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Нет запланированной покупки")

    return header


@router.patch("/groups/{group_id}/purchase/plan", response_model=PurchaseHeaderOut)
def set_plan_date(
    group_id: int,
    payload: PlanDateUpdate,
    session: Session = Depends(get_session),
) -> PurchaseHeaderOut:
    return shopping.set_plan_date(session, group_id, payload.plan_date)


@router.post(
    "/groups/{group_id}/purchase/checkout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def checkout_purchase(
    group_id: int,
    payload: PurchaseCheckout,
    request: Request,
    session: Session = Depends(get_session),
):
    try:
        ids = shopping.checkout_purchase(session, group_id, payload)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    if hasattr(request.state, "offline_connection"):
        return JSONResponse({"ids": ids})
