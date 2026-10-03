"""Зависимости FastAPI, общие для роутеров."""

from fastapi import Header, HTTPException, status

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
