from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..models import (
    Product,
    ProductCategory,
    StoragePlace,
    UnitOfMeasurement,
    UserGroupProduct,
    UserGroupProductConsumption,
    UserGroupProductWaste,
)
from ..schemas import PantryItemCreate
from . import catalog, storage


def list_categories(session: Session) -> Sequence[ProductCategory]:
    return session.scalars(select(ProductCategory).order_by(ProductCategory.id)).all()


def list_units(session: Session) -> Sequence[UnitOfMeasurement]:
    return session.scalars(select(UnitOfMeasurement).order_by(UnitOfMeasurement.id)).all()


def list_places(session: Session) -> Sequence[StoragePlace]:
    return session.scalars(select(StoragePlace).order_by(StoragePlace.id)).all()


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
            Product.expires_in,
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
            UserGroupProduct.price,
            UserGroupProduct.best_before,
            UserGroupProduct.id_product_category,
            UserGroupProduct.id_storage_place,
            UserGroupProduct.is_consumed,
            UserGroupProduct.is_wasted,
            UserGroupProduct.is_deleted,
            UserGroupProduct.is_over,
            remaining.label("remaining"),
            ProductCategory.name.label("category_name"),
            StoragePlace.name.label("storage_place"),
            UnitOfMeasurement.name.label("unit"),
            # За сколько дней до конца срока предупреждать — настройка самого продукта.
            Product.first_reminder_days,
            Product.second_reminder_days,
            UserGroupProduct.first_reminder_shown,
            UserGroupProduct.first_reminder_seen,
            UserGroupProduct.second_reminder_shown,
            UserGroupProduct.second_reminder_seen,
        )
        .outerjoin(Product, Product.id == UserGroupProduct.id_product)
        .outerjoin(
            ProductCategory,
            ProductCategory.id == UserGroupProduct.id_product_category,
        )
        .outerjoin(
            StoragePlace,
            StoragePlace.id == UserGroupProduct.id_storage_place,
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


def money(value: float | None) -> Decimal | None:
    """Цена необязательна, а float переводим в Decimal через строку — без потери копеек."""
    return None if value is None else Decimal(str(value))


def create_pantry_item(
    session: Session, group_id: int, payload: PantryItemCreate, user_id: int
) -> dict:
    """Кладёт продукт в кладовую, заводя справочники, если их ещё нет."""
    unit = session.get(UnitOfMeasurement, payload.unit_id)
    if unit is None:
        raise ValueError("Единица измерения не найдена")

    name = payload.name.strip()
    product, category = catalog.ensure_product(
        session, name, payload.category, payload.product_id, user_id=user_id
    )

    item = UserGroupProduct(
        id_user_group=group_id,
        id_product=product.id,
        product_name=name,
        id_unit_of_measurement=unit.id,
        quantity=Decimal(str(payload.quantity)),
        price=money(payload.price),
        best_before=payload.best_before,
        id_product_category=category.id,
        id_storage_place=payload.storage_place_id
        or storage.place_id_for(session, name, category.name),
    )
    session.add(item)
    session.commit()

    return get_product(session, group_id, item.id)


# Совпадает с SOON_THRESHOLD_DAYS на фронте, если у продукта нет своего порога.
DEFAULT_FIRST_REMINDER_DAYS = 4


def _catalog_days(value) -> int | None:
    if value is None:
        return None
    days = int(value)
    return days if days >= 0 else None


def _days_left(row) -> int:
    return (row["best_before"] - date.today()).days


def _first_threshold(row) -> int:
    days = _catalog_days(row["first_reminder_days"])
    return DEFAULT_FIRST_REMINDER_DAYS if days is None else days


def _in_first_window(row) -> bool:
    return _days_left(row) <= _first_threshold(row)


def _in_second_window(row) -> bool:
    days = _catalog_days(row["second_reminder_days"])
    return days is not None and _days_left(row) <= days


def _reminder_stage(row) -> str | None:
    """Какое напоминание сейчас висит в колокольчике."""
    if row.get("first_reminder_seen") is None and _in_first_window(row):
        return "first"
    if (
        row.get("first_reminder_seen") is not None
        and row.get("second_reminder_seen") is None
        and _in_second_window(row)
    ):
        return "second"
    return None


def _attention_rows(session: Session, group_id: int) -> list[dict]:
    rows = []
    for row in list_products(session, group_id):
        item = dict(row)
        stage = _reminder_stage(item)
        if stage is None:
            continue
        item["reminder_stage"] = stage
        rows.append(item)
    return rows


def _stamp_reminders(
    session: Session,
    group_id: int,
    ids: list[int],
    shown_column,
    seen_column=None,
    now: datetime | None = None,
) -> None:
    if not ids:
        return

    values = {shown_column.key: func.coalesce(shown_column, now)}
    where = [
        UserGroupProduct.id.in_(ids),
        UserGroupProduct.id_user_group == group_id,
    ]
    if seen_column is None:
        values = {shown_column.key: now}
        where.append(shown_column.is_(None))
    else:
        values[seen_column.key] = now
        where.append(seen_column.is_(None))

    session.execute(update(UserGroupProduct).where(*where).values(**values))


def list_reminders(session: Session, group_id: int) -> list[dict]:
    """Список колокольчика: помечает shown при первом попадании на этап."""
    rows = _attention_rows(session, group_id)
    now = datetime.now().astimezone()
    first_ids = [
        row["id"]
        for row in rows
        if row["reminder_stage"] == "first" and row.get("first_reminder_shown") is None
    ]
    second_ids = [
        row["id"]
        for row in rows
        if row["reminder_stage"] == "second" and row.get("second_reminder_shown") is None
    ]

    _stamp_reminders(session, group_id, first_ids, UserGroupProduct.first_reminder_shown, now=now)
    _stamp_reminders(
        session, group_id, second_ids, UserGroupProduct.second_reminder_shown, now=now
    )
    if first_ids or second_ids:
        session.commit()
        for row in rows:
            if row["id"] in first_ids:
                row["first_reminder_shown"] = now
            if row["id"] in second_ids:
                row["second_reminder_shown"] = now

    return rows


def mark_reminders_seen(session: Session, group_id: int) -> None:
    """После просмотра списка ставит seen для текущего этапа напоминания."""
    rows = _attention_rows(session, group_id)
    now = datetime.now().astimezone()
    first_ids = [row["id"] for row in rows if row["reminder_stage"] == "first"]
    second_ids = [row["id"] for row in rows if row["reminder_stage"] == "second"]

    _stamp_reminders(
        session,
        group_id,
        first_ids,
        UserGroupProduct.first_reminder_shown,
        UserGroupProduct.first_reminder_seen,
        now,
    )
    _stamp_reminders(
        session,
        group_id,
        second_ids,
        UserGroupProduct.second_reminder_shown,
        UserGroupProduct.second_reminder_seen,
        now,
    )
    if first_ids or second_ids:
        session.commit()


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
