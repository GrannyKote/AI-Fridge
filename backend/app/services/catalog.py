"""Справочники: продукт и категория заводятся, если их ещё нет."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Product, ProductCategory
from . import storage


def _find_by_name(session: Session, model, name: str):
    statement = select(model).where(func.lower(model.name) == name.strip().lower())
    return session.scalars(statement).first()


def capitalized_name(name: str) -> str:
    name = name.strip()
    return name[:1].upper() + name[1:]


def ensure_product(
    session: Session,
    name: str,
    category_name: str,
    product_id: int | None = None,
    *,
    user_id: int,
) -> tuple[Product, ProductCategory]:
    category = _find_by_name(session, ProductCategory, category_name)
    if category is None:
        category = ProductCategory(name=category_name.strip())
        session.add(category)
        session.flush()

    product = session.get(Product, product_id) if product_id else None
    if product is None:
        product = _find_by_name(session, Product, name)
    if product is None:
        product_name = capitalized_name(name)
        product = Product(
            name=product_name,
            id_product_category=category.id,
            id_user_created=user_id,
            datetime_created=datetime.now().astimezone(),
            id_storage_place=storage.place_id_for(session, product_name, category.name),
        )
        session.add(product)
        session.flush()

    return product, category
