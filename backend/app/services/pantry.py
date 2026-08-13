from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    Product,
    ProductCategory,
    UnitOfMeasurement,
    UserGroupProduct,
    UserGroupProductConsumption,
    UserGroupProductWaste,
)
from ..schemas import PantryItemCreate


def list_categories(session: Session) -> Sequence[ProductCategory]:
    return session.scalars(select(ProductCategory).order_by(ProductCategory.id)).all()


def list_units(session: Session) -> Sequence[UnitOfMeasurement]:
    return session.scalars(select(UnitOfMeasurement).order_by(UnitOfMeasurement.id)).all()


def search_products(session: Session, query: str, limit: int = 5):
    prefix = query.strip().lower()

    if not prefix:
        return []

    # Экранируем спецсимволы LIKE, чтобы они искались буквально.
    for symbol in ("\\", "%", "_"):
        prefix = prefix.replace(symbol, f"\\{symbol}")

    statement = (
        select(
            Product.id,
            Product.name,
            Product.id_product_category.label("category_id"),
            ProductCategory.name.label("category"),
        )
        .outerjoin(ProductCategory, ProductCategory.id == Product.id_product_category)
        .where(func.lower(Product.name).like(f"{prefix}%", escape="\\"))
        .order_by(Product.name)
        .limit(limit)
    )

    return session.execute(statement).mappings().all()


def _written_off(model) -> Decimal:
    """Сколько уже списано по строке кладовой: съедено или выброшено."""
    return (
        select(func.coalesce(func.sum(model.quantity), 0))
        .where(model.id_user_group_product == UserGroupProduct.id)
        .scalar_subquery()
    )


def _products_statement():
    remaining = (
        UserGroupProduct.quantity
        - _written_off(UserGroupProductConsumption)
        - _written_off(UserGroupProductWaste)
    )

    return (
        select(
            UserGroupProduct.id,
            UserGroupProduct.product_name,
            UserGroupProduct.quantity,
            UserGroupProduct.best_before,
            UserGroupProduct.id_product_category,
            UserGroupProduct.is_consumed,
            UserGroupProduct.is_wasted,
            UserGroupProduct.is_deleted,
            UserGroupProduct.is_over,
            remaining.label("remaining"),
            ProductCategory.name.label("category_name"),
            UnitOfMeasurement.name.label("unit"),
        )
        .outerjoin(
            ProductCategory,
            ProductCategory.id == UserGroupProduct.id_product_category,
        )
        .outerjoin(
            UnitOfMeasurement,
            UnitOfMeasurement.id == UserGroupProduct.id_unit_of_measurement,
        )
    )


def list_products(session: Session, group_id: int):
    statement = (
        _products_statement()
        .where(
            UserGroupProduct.id_user_group == group_id,
            # Списанные до нуля и ошибочно заведённые строки не показываем.
            UserGroupProduct.is_over.is_not(True),
            UserGroupProduct.is_deleted.is_not(True),
        )
        .order_by(UserGroupProduct.best_before, UserGroupProduct.id)
    )
    return session.execute(statement).mappings().all()


def get_product(session: Session, group_id: int, item_id: int):
    statement = _products_statement().where(
        UserGroupProduct.id == item_id,
        UserGroupProduct.id_user_group == group_id,
    )
    return session.execute(statement).mappings().first()


def _find_by_name(session: Session, model, name: str):
    statement = select(model).where(func.lower(model.name) == name.strip().lower())
    return session.scalars(statement).first()


def create_pantry_item(session: Session, group_id: int, payload: PantryItemCreate) -> dict:
    """Кладёт продукт в кладовую, заводя справочники, если их ещё нет."""
    unit = session.get(UnitOfMeasurement, payload.unit_id)
    if unit is None:
        raise ValueError("Единица измерения не найдена")

    name = payload.name.strip()
    category_name = payload.category.strip()

    category = _find_by_name(session, ProductCategory, category_name)
    if category is None:
        category = ProductCategory(name=category_name)
        session.add(category)
        session.flush()

    product = session.get(Product, payload.product_id) if payload.product_id else None
    if product is None:
        product = _find_by_name(session, Product, name)
    if product is None:
        product = Product(name=name, id_product_category=category.id)
        session.add(product)
        session.flush()

    item = UserGroupProduct(
        id_user_group=group_id,
        id_product=product.id,
        product_name=name,
        id_unit_of_measurement=unit.id,
        quantity=Decimal(str(payload.quantity)),
        best_before=payload.best_before,
        id_product_category=category.id,
    )
    session.add(item)
    session.commit()

    return get_product(session, group_id, item.id)


def _total_of(session: Session, model, item_id: int) -> Decimal:
    statement = select(func.coalesce(func.sum(model.quantity), 0)).where(
        model.id_user_group_product == item_id
    )
    return session.scalar(statement)


def _update_flags(session: Session, item_id: int) -> None:
    """Закрывает строку кладовой, когда весь продукт списан."""
    item = session.get(UserGroupProduct, item_id)
    consumed = _total_of(session, UserGroupProductConsumption, item_id)
    wasted = _total_of(session, UserGroupProductWaste, item_id)

    if consumed + wasted >= item.quantity:
        item.is_over = True

    if consumed >= item.quantity:
        item.is_consumed = True

    if wasted >= item.quantity:
        item.is_wasted = True


def _checked_amount(row, quantity: float | None) -> Decimal:
    if quantity is None:
        raise ValueError("Укажите количество")

    amount = Decimal(str(quantity))
    remaining = Decimal(row["remaining"])

    if amount > remaining:
        # :f — иначе Decimal печатает круглые числа как 1.5E+2.
        raise ValueError(f"Доступно только {remaining.normalize():f}")

    return amount


def consume_product(session: Session, group_id: int, item_id: int, quantity: float):
    """Записывает потребление и закрывает строку, если продукт закончился."""
    row = get_product(session, group_id, item_id)

    if row is None:
        return None

    session.add(
        UserGroupProductConsumption(
            id_user_group_product=item_id,
            quantity=_checked_amount(row, quantity),
            date_time=datetime.now(),
        )
    )
    session.flush()
    _update_flags(session, item_id)
    session.commit()

    return get_product(session, group_id, item_id)


def waste_product(
    session: Session,
    group_id: int,
    item_id: int,
    reason: str,
    quantity: float | None,
):
    """Списывает испорченный продукт или помечает строку ошибочной."""
    row = get_product(session, group_id, item_id)

    if row is None:
        return None

    if reason == "mistake":
        item = session.get(UserGroupProduct, item_id)
        item.is_deleted = True
    else:
        session.add(
            UserGroupProductWaste(
                id_user_group_product=item_id,
                quantity=_checked_amount(row, quantity),
                date_time=datetime.now(),
            )
        )
        session.flush()
        _update_flags(session, item_id)

    session.commit()

    return get_product(session, group_id, item_id)
