"""Список новостей, отметка прочтения и правки администратора."""

from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import News, NewsUpdate, PersonalNews, User, UserNewsSeen


def list_news(session: Session, user_id: int) -> list[dict]:
    news_statement = (
        select(News, UserNewsSeen.id)
        .outerjoin(
            UserNewsSeen,
            and_(UserNewsSeen.id_news == News.id, UserNewsSeen.id_user_seen == user_id),
        )
        .where(News.is_deleted.is_not(True))
    )
    regular = [
        {
            "id": news.id,
            "header": news.header,
            "is_seen": seen_id is not None,
            "is_personal": False,
            "_sort": news.datetime_created,
        }
        for news, seen_id in session.execute(news_statement)
    ]

    personal_statement = (
        select(PersonalNews)
        .where(PersonalNews.id_user == user_id)
        .order_by(PersonalNews.datetime_created.desc(), PersonalNews.id.desc())
    )
    personal = [
        {
            "id": item.id,
            "header": item.header,
            "is_seen": item.datetime_seen is not None,
            "is_personal": True,
            "_sort": item.datetime_created,
        }
        for item in session.scalars(personal_statement)
    ]

    merged = sorted(
        regular + personal,
        key=lambda row: (row["_sort"], row["id"]),
        reverse=True,
    )
    return [
        {
            "id": row["id"],
            "header": row["header"],
            "is_seen": row["is_seen"],
            "is_personal": row["is_personal"],
        }
        for row in merged
    ]


def get_news(session: Session, news_id: int) -> News | None:
    news = session.get(News, news_id)
    if news is None or news.is_deleted:
        return None
    return news


def get_personal_news(session: Session, personal_id: int, user_id: int) -> PersonalNews | None:
    item = session.get(PersonalNews, personal_id)
    if item is None or item.id_user != user_id:
        return None
    return item


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


def mark_personal_seen(session: Session, user_id: int, personal_id: int) -> PersonalNews | None:
    item = get_personal_news(session, personal_id, user_id)
    if item is None:
        return None

    if item.datetime_seen is None:
        item.datetime_seen = datetime.now().astimezone()
        session.commit()
        session.refresh(item)

    return item


def create_news(
    session: Session,
    user_id: int,
    header: str,
    body: str,
) -> News:
    news = News(
        id_user_created=user_id,
        datetime_created=datetime.now().astimezone(),
        header=header.strip(),
        body=body.strip() or None,
        is_deleted=False,
    )
    session.add(news)
    session.commit()
    session.refresh(news)
    return news


def list_all(session: Session) -> list[News]:
    statement = (
        select(News)
        .where(News.is_deleted.is_not(True))
        .order_by(News.datetime_created.desc(), News.id.desc())
    )
    return list(session.scalars(statement))


def update_news(
    session: Session,
    user_id: int,
    news_id: int,
    header: str,
    body: str,
) -> News | None:
    news = get_news(session, news_id)
    if news is None:
        return None

    news.header = header.strip()
    news.body = body.strip() or None
    session.add(
        NewsUpdate(
            id_user_updated=user_id,
            datetime_updated=datetime.now().astimezone(),
        )
    )
    session.commit()
    session.refresh(news)
    return news


def list_news_viewers(session: Session, news_id: int) -> list[dict] | None:
    if get_news(session, news_id) is None:
        return None

    statement = (
        select(User.login, UserNewsSeen.datetime_seen)
        .join(User, User.id == UserNewsSeen.id_user_seen)
        .where(UserNewsSeen.id_news == news_id)
        .order_by(UserNewsSeen.datetime_seen.desc())
    )
    return [
        {"login": login, "datetime_seen": datetime_seen}
        for login, datetime_seen in session.execute(statement)
    ]


def delete_news(session: Session, user_id: int, news_id: int) -> bool:
    news = get_news(session, news_id)
    if news is None:
        return False

    news.is_deleted = True
    session.add(
        NewsUpdate(
            id_user_updated=user_id,
            datetime_updated=datetime.now().astimezone(),
        )
    )
    session.commit()
    return True
