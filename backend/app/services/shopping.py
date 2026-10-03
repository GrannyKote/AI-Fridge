"""Список покупок группы."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Product,
    ProductCategory,
    StoragePlace,
    UnitOfMeasurement,
    UserGroupProduct,
    UserGroupPurchase,
    UserGroupPurchaseProduct,
)
from ..schemas import PurchaseCheckout, PurchaseCreate
from . import catalog
from .pantry import money


def _product_statement():
    return (
        select(
            UserGroupPurchaseProduct.id,
            UserGroupPurchaseProduct.product_name,
            UserGroupPurchaseProduct.quantity,
            UserGroupPurchaseProduct.id_product_category,
            ProductCategory.name.label("category_name"),
            UnitOfMeasurement.name.label("unit"),
            # Срок хранения из справочника: подставится в срок годности при расчёте покупок.
            Product.expires_in,
        )
        .outerjoin(Product, Product.id == UserGroupPurchaseProduct.id_product)
        .outerjoin(
            ProductCategory,
            ProductCategory.id == UserGroupPurchaseProduct.id_product_category,
        )
        .outerjoin(
            UnitOfMeasurement,
            UnitOfMeasurement.id == UserGroupPurchaseProduct.id_unit_of_measurement,
        )
    )


def _open_purchase(session: Session, group_id: int) -> UserGroupPurchase | None:
    statement = (
        select(UserGroupPurchase)
        .where(
            UserGroupPurchase.id_user_group == group_id,
            UserGroupPurchase.actual_date.is_(None),
        )
        .order_by(UserGroupPurchase.id.desc())
        .limit(1)
    )
    return session.scalars(statement).first()


def _ensure_open_purchase(
    session: Session, group_id: int, created_at: datetime
) -> UserGroupPurchase:
    purchase = _open_purchase(session, group_id)
    if purchase is not None:
        return purchase

    purchase = UserGroupPurchase(
        id_user_group=group_id,
        create_date_time=created_at,
    )
    session.add(purchase)
    session.flush()
    return purchase


def list_purchases(session: Session, group_id: int):
    purchase = _open_purchase(session, group_id)
    if purchase is None:
        return []

    statement = (
        _product_statement()
        .where(
            UserGroupPurchaseProduct.id_user_group_purchase == purchase.id,
            UserGroupPurchaseProduct.is_deleted.is_not(True),
            UserGroupPurchaseProduct.is_purchased.is_not(True),
        )
        .order_by(UserGroupPurchaseProduct.id)
    )
    return session.execute(statement).mappings().all()


def get_purchase(session: Session, group_id: int, item_id: int):
    statement = (
        _product_statement()
        .where(
            UserGroupPurchaseProduct.id == item_id,
            UserGroupPurchaseProduct.id_user_group == group_id,
            UserGroupPurchaseProduct.is_deleted.is_not(True),
            UserGroupPurchaseProduct.is_purchased.is_not(True),
        )
    )
    return session.execute(statement).mappings().first()


def create_purchase(
    session: Session, group_id: int, payload: PurchaseCreate, user_id: int
):
    unit = session.get(UnitOfMeasurement, payload.unit_id)
    if unit is None:
        raise ValueError("Единица измерения не найдена")

    name = catalog.capitalized_name(payload.name)
    product, category = catalog.ensure_product(
        session, name, payload.category, payload.product_id, user_id=user_id
    )
    now = datetime.now()
    purchase = _ensure_open_purchase(session, group_id, now)

    item = UserGroupPurchaseProduct(
        id_user_group=group_id,
        id_product=product.id,
        product_name=name,
        id_unit_of_measurement=unit.id,
        quantity=Decimal(str(payload.quantity)),
        id_product_category=category.id,
        id_user_group_purchase=purchase.id,
        create_date_time=now,
    )
    session.add(item)
    session.commit()

    return get_purchase(session, group_id, item.id)


def delete_purchase_product(session: Session, group_id: int, item_id: int) -> bool:
    item = session.get(UserGroupPurchaseProduct, item_id)
    if item is None or item.id_user_group != group_id or item.is_deleted or item.is_purchased:
        return False

    purchase = session.get(UserGroupPurchase, item.id_user_group_purchase)
    if purchase is None or purchase.actual_date is not None:
        return False

    item.is_deleted = True
    session.commit()
    return True


def get_purchase_header(session: Session, group_id: int) -> UserGroupPurchase | None:
    statement = (
        select(UserGroupPurchase)
        .where(
            UserGroupPurchase.id_user_group == group_id,
            UserGroupPurchase.plan_date.is_not(None),
            UserGroupPurchase.actual_date.is_(None),
        )
        .order_by(UserGroupPurchase.plan_date, UserGroupPurchase.id.desc())
        .limit(1)
    )
    return session.scalars(statement).first()


def set_plan_date(session: Session, group_id: int, plan_date: date) -> UserGroupPurchase:
    purchase = _ensure_open_purchase(session, group_id, datetime.now())
    purchase.plan_date = plan_date
    session.commit()
    session.refresh(purchase)
    return purchase


def checkout_purchase(session: Session, group_id: int, payload: PurchaseCheckout) -> None:
    purchase = _open_purchase(session, group_id)
    if purchase is None:
        raise ValueError("Нет открытого списка покупок")

    seen: set[int] = set()
    now = datetime.now()

    for item in payload.items:
        if item.id in seen:
            raise ValueError("Товар в списке повторяется")
        seen.add(item.id)

        row = session.get(UserGroupPurchaseProduct, item.id)
        if (
            row is None
            or row.id_user_group != group_id
            or row.id_user_group_purchase != purchase.id
            or row.is_deleted
            or row.is_purchased
        ):
            raise ValueError("Товар не найден в списке покупок")

        place = session.get(StoragePlace, item.storage_place_id)
        if place is None:
            raise ValueError("Место хранения не найдено")

        session.add(
            UserGroupProduct(
                id_user_group=group_id,
                id_product=row.id_product,
                product_name=catalog.capitalized_name(row.product_name),
                id_unit_of_measurement=row.id_unit_of_measurement,
                quantity=Decimal(str(item.quantity)),
                price=money(item.price),
                best_before=item.best_before,
                id_product_category=row.id_product_category,
                id_storage_place=place.id,
            )
        )
        row.is_purchased = True

    purchase.actual_date = now
    session.commit()
