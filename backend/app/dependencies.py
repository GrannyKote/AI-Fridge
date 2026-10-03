"""Зависимости FastAPI, общие для роутеров."""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_session
from .models import User
from .services import tokens


def current_user_id(authorization: str = Header(default="")) -> int:
    """id пользователя из заголовка `Authorization: Bearer <токен>`."""
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Нужен вход в приложение")

    try:
        return tokens.read_user_id(token.strip())
    except ValueError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error


def current_admin_id(
    session: Session = Depends(get_session),
    user_id: int = Depends(current_user_id),
) -> int:
    """id администратора. Обычному пользователю отвечает 403."""
    user = session.get(User, user_id)
    if user is None or not bool(user.is_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нужны права администратора")
    return user_id
