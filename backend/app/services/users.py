from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import CreatedUser, LoginAttempt, User, UserGroup, UserGroupUser


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
            user_agent=user_agent,
            ip=ip,
        )
    )
    session.commit()

    return user, group


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
            user_agent=user_agent,
            ip=ip,
            is_success=is_success,
        )
    )
    session.commit()
