from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import CreatedUser, LoginAttempt, User, UserGroup, UserGroupUser


def _clip(value: str, max_len: int) -> str:
    text = value or ""
    return text if len(text) <= max_len else text[:max_len]


def find_by_login(session: Session, login: str) -> User | None:
    statement = select(User).where(func.lower(User.login) == login.strip().lower())
    return session.scalars(statement).first()


def list_groups(session: Session, user_id: int) -> list[UserGroup]:
    statement = (
        select(UserGroup)
        .join(UserGroupUser, UserGroupUser.id_user_group == UserGroup.id)
        .where(UserGroupUser.id_user == user_id)
        .order_by(UserGroup.id)
    )
    return list(session.scalars(statement))


def create_with_group(
    session: Session,
    login: str,
    password: str,
    *,
    user_agent: str = "",
    ip: str = "",
) -> tuple[User, UserGroup]:
    """Создаёт пользователя и сразу его личную группу — одной транзакцией."""
    user = User(login=login.strip(), password=password, is_admin=False)
    session.add(user)
    session.flush()

    group = UserGroup(name=settings.default_group_name)
    session.add(group)
    session.flush()

    session.add(UserGroupUser(id_user=user.id, id_user_group=group.id))
    now = datetime.now().astimezone()
    session.add(
        CreatedUser(
            login=user.login,
            date_time=now,
            user_agent=_clip(user_agent, 512),
            ip=_clip(ip, 256),
        )
    )
    session.commit()

    return user, group


def list_for_admin(session: Session) -> list[dict]:
    registration = (
        select(
            func.lower(CreatedUser.login).label("login_key"),
            func.min(CreatedUser.date_time).label("datetime_registered"),
        )
        .group_by(func.lower(CreatedUser.login))
        .subquery()
    )
    statement = (
        select(User.id, User.login, registration.c.datetime_registered)
        .outerjoin(registration, func.lower(User.login) == registration.c.login_key)
        .order_by(User.login.asc())
    )
    rows = session.execute(statement).all()
    return [
        {
            "id": row.id,
            "login": row.login,
            "datetime_registered": row.datetime_registered,
        }
        for row in rows
    ]


def set_password(session: Session, user_id: int, password: str) -> User | None:
    user = session.get(User, user_id)
    if user is None:
        return None
    user.password = password
    session.commit()
    session.refresh(user)
    return user


def record_login_attempt(
    session: Session,
    login: str,
    *,
    is_success: bool,
    user_agent: str = "",
    ip: str = "",
) -> None:
    session.add(
        LoginAttempt(
            login=login.strip(),
            date_time=datetime.now().astimezone().timetz(),
            user_agent=_clip(user_agent, 512),
            ip=_clip(ip, 256),
            is_success=is_success,
        )
    )
    session.commit()
