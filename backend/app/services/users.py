from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User, UserGroup, UserGroupUser


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


def create_with_group(session: Session, login: str, password: str) -> tuple[User, UserGroup]:
    """Создаёт пользователя и сразу его личную группу — одной транзакцией."""
    user = User(login=login.strip(), password=password)
    session.add(user)
    session.flush()

    group = UserGroup(name=settings.default_group_name)
    session.add(group)
    session.flush()

    session.add(UserGroupUser(id_user=user.id, id_user_group=group.id))
    session.commit()

    return user, group
