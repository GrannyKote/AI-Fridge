"""JWT доступа: id пользователя подписывается при входе и приходит обратно в запросах."""

from datetime import datetime, timedelta

import jwt

from ..config import settings
from ..models import User


def create_access_token(user: User) -> str:
    issued_at = datetime.now().astimezone()
    payload = {
        "sub": str(user.id),
        "login": user.login,
        "iat": issued_at,
        "exp": issued_at + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def read_user_id(token: str) -> int:
    """Достаёт id пользователя из токена. ValueError — токен просрочен или подделан."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as error:
        raise ValueError("Вход устарел, войдите заново") from error
    except jwt.InvalidTokenError as error:
        raise ValueError("Неверный токен доступа") from error

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject.isdigit():
        raise ValueError("В токене нет пользователя")

    return int(subject)
