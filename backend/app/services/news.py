"""Список новостей и отметка прочтения."""

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import News, UserNewsSeen


def list_news(session: Session, user_id: int) -> list[dict]:
    statement = (
        select(News, UserNewsSeen.id)
        .outerjoin(
            UserNewsSeen,
            and_(UserNewsSeen.id_news == News.id, UserNewsSeen.id_user_seen == user_id),
        )
        .order_by(News.datetime_created.desc(), News.id.desc())
    )
    return [
        {
            "id": news.id,
            "header": news.header,
            "is_seen": seen_id is not None,
        }
        for news, seen_id in session.execute(statement)
    ]


def get_news(session: Session, news_id: int) -> News | None:
    return session.get(News, news_id)


def mark_seen(session: Session, user_id: int, news_id: int) -> News | None:
    news = get_news(session, news_id)
    if news is None:
        return None

    already = session.scalar(
        select(UserNewsSeen.id).where(
            UserNewsSeen.id_news == news_id,
            UserNewsSeen.id_user_seen == user_id,
        )
    )
    if already is None:
        session.add(
            UserNewsSeen(
                id_news=news_id,
                id_user_seen=user_id,
                datetime_seen=datetime.now().astimezone(),
            )
        )
        session.commit()

    return news
