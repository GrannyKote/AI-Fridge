from collections.abc import Sequence
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select, text, update
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


def shelf_lookup_name(name: str, catalog_names: Sequence[str]) -> str | None:
    """Точное имя каталога или самое длинное базовое имя внутри строки."""
    cleaned = name.strip()
    if not cleaned:
        return None

    by_fold = {}
    for item in catalog_names:
        text_name = item.strip()
        if text_name:
            by_fold.setdefault(text_name.lower().replace("ё", "е"), text_name)

    folded = cleaned.lower().replace("ё", "е")
    if folded in by_fold:
        return by_fold[folded]

    snapped = snap_to_catalog(cleaned, catalog_names)
    snapped_fold = snapped.lower().replace("ё", "е")
    if snapped_fold == folded:
        return None
    return by_fold.get(snapped_fold)


def shelf_life(session: Session, name: str) -> tuple[str, int] | None:
    """Срок базового продукта. «Молоко 2.5%» берёт срок у «молоко»."""
    names = session.execute(
        text(
            """
            SELECT name
            FROM ml.base_product
            WHERE shelf_life_days IS NOT NULL
            """
        )
    ).scalars().all()
    lookup = shelf_lookup_name(name, names)
    if lookup is None:
        return None

    row = session.execute(
        text(
            """
            SELECT name, shelf_life_days
            FROM ml.base_product
            WHERE lower(name) = lower(:name)
              AND shelf_life_days IS NOT NULL
            """
        ),
        {"name": lookup},
    ).first()
    if row is None:
        return None
    return row.name, int(row.shelf_life_days)


def remember_shelf_life(session: Session, name: str, days: int) -> tuple[str, int]:
    """Запоминает имя и срок. То же имя без учёта регистра обновляет дни, новое имя добавляется."""
    cleaned = name.strip()
    row = session.execute(
        text(
            """
            SELECT id, name
            FROM ml.base_product
            WHERE lower(name) = lower(:name)
            """
        ),
        {"name": cleaned},
    ).first()
    if row is None:
        session.execute(
            text(
                """
                INSERT INTO ml.base_product (name, shelf_life_days)
                VALUES (:name, :days)
                """
            ),
            {"name": cleaned, "days": days},
        )
        saved = cleaned
    else:
        session.execute(
            text(
                """
                UPDATE ml.base_product
                SET shelf_life_days = :days
                WHERE id = :id
                """
            ),
            {"days": days, "id": row.id},
        )
        saved = row.name
    session.commit()
    return saved, days


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
            UserGroupProduct.purchased_on,
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
        )
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


def collapse_same_batches(session: Session, group_id: int) -> None:
    """Складывает открытые строки с одним названием, сроком, единицей, местом и днём покупки.

    Пустой день покупки у старых строк считается одним и тем же: такие строки тоже сходятся.
    """
    rows = session.scalars(
        select(UserGroupProduct).where(
            UserGroupProduct.id_user_group == group_id,
            UserGroupProduct.is_deleted.is_not(True),
            UserGroupProduct.is_over.is_not(True),
        )
    ).all()
    batches: dict[tuple, list[UserGroupProduct]] = {}
    for row in rows:
        key = (
            row.product_name,
            row.id_unit_of_measurement,
            row.id_storage_place,
            row.best_before,
            row.purchased_on,
        )
        batches.setdefault(key, []).append(row)

    changed = False
    for batch in batches.values():
        if len(batch) < 2:
            continue
        batch.sort(key=lambda item: item.id)
        keep = batch[0]
        for extra in batch[1:]:
            keep.quantity = keep.quantity + extra.quantity
            for model in (UserGroupProductConsumption, UserGroupProductWaste):
                session.execute(
                    update(model)
                    .where(model.id_user_group_product == extra.id)
                    .values(id_user_group_product=keep.id)
                )
            session.delete(extra)
        session.flush()
        _update_flags(session, keep.id)
        changed = True
    if changed:
        session.commit()


def list_products(session: Session, group_id: int):
    collapse_same_batches(session, group_id)
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


def stored_name(name: str) -> str:
    """Один вид написания. «мясО» становится «Мясо», «Сыр Гауда» остаётся «Сыр Гауда»."""
    text = " ".join(name.split())
    if not text:
        return text
    chars = []
    for index, char in enumerate(text):
        if index == 0:
            chars.append(char.upper())
        elif char.isupper() and text[index - 1].isalpha():
            chars.append(char.lower())
        else:
            chars.append(char)
    return "".join(chars)


def product_name_for_pantry(name: str, catalog_names: Sequence[str]) -> str:
    """«мясо» и «мясО» становятся «Мясо». «Молоко 2.5%» и «Молоко 3.5%» остаются разными."""
    snapped = snap_to_catalog(name, catalog_names)
    raw_fold = name.strip().lower().replace("ё", "е")
    snap_fold = snapped.lower().replace("ё", "е")
    if snap_fold != raw_fold and any(ch.isdigit() for ch in name):
        return stored_name(name)
    return stored_name(snapped)


def snap_to_catalog(name: str, catalog_names: Sequence[str]) -> str:
    """Самое длинное базовое имя внутри введённого. Бренд остаётся за пределами имени."""
    cleaned = name.strip()
    folded = cleaned.lower().replace("ё", "е")
    if not folded:
        return cleaned

    best = ""
    best_len = 0
    for item in catalog_names:
        candidate = item.strip().lower().replace("ё", "е")
        if candidate and _has_term(folded, candidate) and len(candidate) > best_len:
            best = item.strip()
            best_len = len(candidate)
    return best or cleaned


def _has_term(folded: str, candidate: str) -> bool:
    start = 0
    while True:
        at = folded.find(candidate, start)
        if at < 0:
            return False
        before = at == 0 or not folded[at - 1].isalnum()
        after = at + len(candidate)
        if before and (after == len(folded) or not folded[after].isalnum()):
            return True
        start = at + 1


def add_or_sum_pantry_item(
    session: Session,
    group_id: int,
    *,
    name: str,
    product_id: int,
    category_id: int,
    unit_id: int,
    quantity: Decimal,
    best_before: date,
    storage_place_id: int | None,
    purchased_on: date,
    user_id: int | None,
) -> int:
    """Складывает покупку с такой же строкой: имя, срок, единица и место.

    День покупки совпадает, либо у уже лежащей строки он ещё не записан.
    """
    collapse_same_batches(session, group_id)
    match = (
        UserGroupProduct.id_user_group == group_id,
        UserGroupProduct.product_name == name,
        UserGroupProduct.id_unit_of_measurement == unit_id,
        UserGroupProduct.best_before == best_before,
        UserGroupProduct.id_storage_place == storage_place_id,
        UserGroupProduct.is_deleted.is_not(True),
        UserGroupProduct.is_over.is_not(True),
    )
    existing = session.scalars(
        select(UserGroupProduct).where(*match, UserGroupProduct.purchased_on == purchased_on)
    ).first()
    if existing is None:
        existing = session.scalars(
            select(UserGroupProduct)
            .where(*match, UserGroupProduct.purchased_on.is_(None))
            .order_by(UserGroupProduct.id)
        ).first()
        if existing is not None:
            existing.purchased_on = purchased_on
    if existing is not None:
        existing.quantity = existing.quantity + quantity
        session.flush()
        _update_flags(session, existing.id)
        return existing.id

    item = UserGroupProduct(
        id_user_group=group_id,
        id_product=product_id,
        product_name=name,
        id_unit_of_measurement=unit_id,
        quantity=quantity,
        best_before=best_before,
        purchased_on=purchased_on,
        id_product_category=category_id,
        id_storage_place=storage_place_id,
        added_at=datetime.now(timezone.utc),
        id_user=user_id,
    )
    session.add(item)
    session.flush()
    return item.id


def create_pantry_item(session: Session, group_id: int, payload: PantryItemCreate) -> dict:
    """Кладёт продукт в кладовую, заводя справочники, если их ещё нет."""
    unit = session.get(UnitOfMeasurement, payload.unit_id)
    if unit is None:
        raise ValueError("Единица измерения не найдена")

    catalog_names = session.execute(text("SELECT name FROM ml.base_product")).scalars().all()
    name = product_name_for_pantry(payload.name, catalog_names)
    product, category = catalog.ensure_product(session, name, payload.category, None)
    place_id = payload.storage_place_id or storage.place_id_for(session, name, category.name)
    item_id = add_or_sum_pantry_item(
        session,
        group_id,
        name=name,
        product_id=product.id,
        category_id=category.id,
        unit_id=unit.id,
        quantity=Decimal(str(payload.quantity)),
        best_before=payload.best_before,
        storage_place_id=place_id,
        purchased_on=payload.purchased_on or date.today(),
        user_id=payload.user_id,
    )
    session.commit()

    return get_product(session, group_id, item_id)


def update_pantry_item(session: Session, group_id: int, item_id: int, payload) -> dict | None:
    """Меняет строку кладовой. quantity — сколько осталось видно в списке."""
    row = get_product(session, group_id, item_id)
    if row is None:
        return None

    unit = session.get(UnitOfMeasurement, payload.unit_id)
    if unit is None:
        raise ValueError("Единица измерения не найдена")
    place = session.get(StoragePlace, payload.storage_place_id)
    if place is None:
        raise ValueError("Место хранения не найдено")

    catalog_names = session.execute(text("SELECT name FROM ml.base_product")).scalars().all()
    name = product_name_for_pantry(payload.name, catalog_names)
    product, category = catalog.ensure_product(session, name, payload.category, None)
    consumed = _total_of(session, UserGroupProductConsumption, item_id)
    wasted = _total_of(session, UserGroupProductWaste, item_id)

    item = session.get(UserGroupProduct, item_id)
    item.product_name = name
    item.id_product = product.id
    item.id_product_category = category.id
    item.id_unit_of_measurement = unit.id
    item.id_storage_place = place.id
    item.quantity = consumed + wasted + Decimal(str(payload.quantity))
    item.best_before = payload.best_before
    item.purchased_on = payload.purchased_on
    _update_flags(session, item_id)
    session.commit()

    return get_product(session, group_id, item_id)


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

    item.is_over = consumed + wasted >= item.quantity
    item.is_consumed = consumed >= item.quantity
    item.is_wasted = wasted >= item.quantity


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
