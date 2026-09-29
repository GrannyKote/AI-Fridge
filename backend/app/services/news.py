"""Новости, которые администратор отправляет пользователям."""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import News, NewsRead, User


def publish(session: Session, admin_id: int, title: str, body: str) -> News | None:
    admin = session.get(User, admin_id)
    if admin is None or admin.user_type != "admin":
        return None

    row = News(title=title, body=body, date_time=datetime.now(timezone.utc))
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_news(session: Session) -> list[News]:
    return list(
        session.scalars(select(News).order_by(News.date_time.desc(), News.id.desc())).all()
    )


def unread(session: Session, user_id: int) -> News | None:
    if session.get(User, user_id) is None:
        return None

    read_ids = select(NewsRead.id_news).where(NewsRead.id_user == user_id)
    return session.scalars(
        select(News).where(News.id.not_in(read_ids)).order_by(News.date_time.desc(), News.id.desc()).limit(1)
    ).first()


def remove(session: Session, admin_id: int, news_id: int) -> bool | None:
    """Удаляет новость у всех. None — нет прав, False — такой новости нет."""
    admin = session.get(User, admin_id)
    if admin is None or admin.user_type != "admin":
        return None

    row = session.get(News, news_id)
    if row is None:
        return False

    session.execute(delete(NewsRead).where(NewsRead.id_news == news_id))
    session.delete(row)
    session.commit()
    return True


def mark_read(session: Session, user_id: int) -> None:
    if session.get(User, user_id) is None:
        return

    seen = set(session.scalars(select(NewsRead.id_news).where(NewsRead.id_user == user_id)).all())
    for news_id in session.scalars(select(News.id)).all():
        if news_id not in seen:
            session.add(NewsRead(id_user=user_id, id_news=news_id))
    session.commit()
