"""Счётчики загрузок в кладовую."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User, UserGroupProduct

WINDOWS = (
    ("day", timedelta(hours=24)),
    ("week", timedelta(days=7)),
    ("month", timedelta(days=30)),
)


def count_uploads(rows: list[tuple[str, int | None, datetime | None]], now: datetime) -> dict:
    """Сколько разных продуктов и сколько пользователей загрузили хотя бы один."""
    result = {}
    for key, delta in WINDOWS:
        since = now - delta
        names: set[str] = set()
        users: set[int] = set()
        for name, user_id, added_at in rows:
            if added_at is None:
                continue
            moment = added_at if added_at.tzinfo else added_at.replace(tzinfo=timezone.utc)
            if moment < since:
                continue
            names.add(name.casefold())
            if user_id is not None:
                users.add(user_id)
        result[key] = {"products": len(names), "users": len(users)}
    return result


def upload_stats(session: Session, admin_id: int) -> dict | None:
    admin = session.get(User, admin_id)
    if admin is None or admin.user_type != "admin":
        return None

    rows = session.execute(
        select(UserGroupProduct.product_name, UserGroupProduct.id_user, UserGroupProduct.added_at)
    ).all()
    counted = count_uploads(rows, datetime.now(timezone.utc))
    return {
        "products": {key: counted[key]["products"] for key, _ in WINDOWS},
        "users": {key: counted[key]["users"] for key, _ in WINDOWS},
    }
